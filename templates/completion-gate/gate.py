#!/usr/bin/env python3
"""Completion gate for coding agents, run as a Claude Code or Codex hook.

Hook usage:  python3 gate.py --harness claude|codex   (payload on stdin)
Self-test:   python3 gate.py --self-test

Events:
  SessionStart, SubagentStart  record a git baseline and announce the gate.
  Stop, SubagentStop           block finishing when this agent changed files
                               and its final message lacks the receipt fields.
  PreToolUse                   before pull request creation, run the configured
                               check and escalate protected-path changes to a
                               person; reserve merges for people.

Configuration lives in <repo>/.agents/gate/config.json (see README.md).
Internal errors exit 2, which blocks Stop and PreToolUse in both harnesses;
a Stop that already retried once is released so a broken gate cannot trap a
session.
"""
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows has no advisory locks; state writes stay atomic.
    fcntl = None

CONFIG_PATH = '.agents/gate/config.json'
DEFAULTS = {
    'receipt': ['VERIFIED:', 'UNVERIFIED:', 'PRECEDENT:', 'CONFIDENCE:'],
    'pr_check': None,
    'pr_check_timeout': 540,
    'protected': [],
    'base_ref': None,
    'human_merge': True,
    'max_stop_blocks': 3,
}
GH_PR = r'''(?:^|[\s;&|('"`/])gh(?:\s+(?:-R|--repo)(?:=|\s+)\S+)*\s+pr\s+'''
PR_CREATE = re.compile(GH_PR + r'(?:create|new)\b')
PR_MERGE = re.compile(GH_PR + r'merge\b')
MCP_CREATE = re.compile(r'^mcp__.+__create_pull_request(?:_\w+)?$')
MCP_MERGE = re.compile(r'^mcp__.+__(?:merge_pull_request|enable_pr_auto_merge)$')
BASE_REFS = ('origin/HEAD', 'origin/main', 'origin/master')
STATE_MAX_AGE = 14 * 86400
TRANSCRIPT_TAIL = 1 << 20


def run(args, cwd, timeout=30, shell=False, stdin=None):
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, timeout=timeout, shell=shell)


def git(root, *args, check=True, stdin=None):
    result = run(['git', *args], root, stdin=stdin)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}")
    return result


def repo_root(cwd):
    result = run(['git', 'rev-parse', '--show-toplevel'], cwd)
    return Path(result.stdout.decode().strip()).resolve() if result.returncode == 0 else None


def head(root):
    result = git(root, 'rev-parse', '--verify', '-q', 'HEAD', check=False)
    return result.stdout.decode().strip() if result.returncode == 0 else None


def names(result):
    return {value.decode(errors='surrogateescape') for value in result.stdout.split(b'\0') if value}


def dirty_paths(root):
    paths = names(git(root, 'diff', '--no-renames', '--name-only', '-z'))
    paths |= names(git(root, 'diff', '--cached', '--no-renames', '--name-only', '-z'))
    return paths | names(git(root, 'ls-files', '--others', '--exclude-standard', '-z'))


def tree_ids(root, commit):
    """Map of path to blob id for every file in a commit."""
    ids = {}
    if commit:
        for entry in git(root, 'ls-tree', '-r', '-z', '--full-tree', commit).stdout.split(b'\0'):
            if entry:
                meta, path = entry.split(b'\t', 1)
                kind, oid = meta.split()[1:3]
                if kind == b'blob':
                    ids[path.decode(errors='surrogateescape')] = oid.decode()
    return ids


def blob_ids(root, paths):
    """Blob ids of working-tree files, using git's own filters; None if absent."""
    ids = dict.fromkeys(paths)
    for p in paths:
        if (root / p).is_symlink():  # git stores the link text, not the target
            link = str(Path(root / p).readlink()).encode(errors='surrogateescape')
            ids[p] = git(root, 'hash-object', '--stdin', stdin=link).stdout.decode().strip()
    files = [p for p in paths if (root / p).is_file() and not (root / p).is_symlink() and '\n' not in p]
    if files:
        out = git(root, 'hash-object', '--stdin-paths', stdin='\n'.join(files).encode(errors='surrogateescape'))
        ids.update(zip(files, out.stdout.decode().split()))
    return ids


def load_config(root):
    path = root / CONFIG_PATH
    config = dict(DEFAULTS)
    if path.is_file():
        config.update(json.loads(path.read_text(encoding='utf8')))
    return config


# State: one file per (worktree, session, agent) inside the git common dir,
# so it is never committed and parallel agents never share a baseline.

def state_dir(root):
    common = Path(git(root, 'rev-parse', '--git-common-dir').stdout.decode().strip())
    return (common if common.is_absolute() else root / common) / 'agent-gate'


def state_path(root, payload):
    identity = f"{root}:{payload.get('session_id', 'unknown')}:{payload.get('agent_id') or 'main'}"
    return state_dir(root) / f'{hashlib.sha256(identity.encode()).hexdigest()}.json'


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def save(path, state):
    pending = path.with_suffix('.tmp')
    pending.write_text(json.dumps(state), encoding='utf8')
    pending.replace(path)


def prune(directory, keep):
    cutoff = time.time() - STATE_MAX_AGE
    for entry in directory.glob('*'):
        try:
            if entry.stem != keep.stem and entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:  # Another agent pruned it first.
            pass


def baseline(root):
    dirty = sorted(dirty_paths(root))
    return {'head': head(root), 'ids': blob_ids(root, dirty), 'stop_blocks': 0}


def load_state(root, path):
    if path.is_file():
        return json.loads(path.read_text(encoding='utf8'))
    # No baseline (hooks installed mid-session): judge everything since HEAD.
    return {'head': head(root), 'ids': {}, 'stop_blocks': 0}


def changed_paths(root, state):
    """Paths whose content differs from the session baseline.

    Compares the whole tree, so edits made through shell commands and commits
    count. In a checkout shared with other agents, their edits count too.
    """
    before = tree_ids(root, state['head'])
    before.update(state['ids'])
    candidates = dirty_paths(root) | set(state['ids'])
    current = head(root)
    if current and current != state['head']:
        if state['head']:
            candidates |= names(git(root, 'diff', '--no-renames', '--name-only', '-z', state['head'], current))
        else:
            candidates |= set(tree_ids(root, current))
    now = blob_ids(root, sorted(candidates))
    return sorted(p for p in candidates if before.get(p) != now[p])


def missing_fields(text, fields):
    # A field counts only as a whole word followed by a value on the same line,
    # so "UNVERIFIED: x" does not satisfy "VERIFIED:".
    return [f for f in fields if not re.search(r'(?<![A-Za-z])' + re.escape(f) + r'[ \t]*\S', text or '')]


def subagent_report(payload):
    """Text the subagent itself wrote last: its final message and any handback.

    Only assistant-authored content counts, never tool results or hook
    feedback, so echoed instructions cannot satisfy the receipt.
    """
    path = payload.get('agent_transcript_path')
    if not path or not Path(path).is_file():
        return ''
    with open(path, 'rb') as handle:
        handle.seek(0, 2)
        handle.seek(max(0, handle.tell() - TRANSCRIPT_TAIL))
        lines = handle.read().split(b'\n')
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        content = entry.get('message', {}).get('content') if isinstance(entry, dict) and entry.get('type') == 'assistant' else None
        if isinstance(content, list):
            entries.append(content)
    parts = [b.get('text', '') for b in (entries[-1] if entries else []) if isinstance(b, dict) and b.get('type') == 'text']
    for content in reversed(entries):
        handbacks = [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_use' and 'handback' in str(b.get('name', '')).lower()]
        if handbacks:
            parts += [str(v) for b in handbacks for v in (b.get('input') or {}).values() if isinstance(v, str)]
            break
    return '\n'.join(parts)


def handle_start(root, payload, event):
    path = state_path(root, payload)
    with locked(path):
        if event == 'SubagentStart' or payload.get('source') in {'startup', 'clear'} or not path.exists():
            save(path, baseline(root))
        prune(path.parent, path)
    config = load_config(root)
    lines = [
        'A completion gate is active in this repository. Load the completion-gate skill before code changes.',
        'If you change files, end your final message with: ' + ', '.join(config['receipt']),
    ]
    if config['pr_check']:
        lines.append(f"Creating a pull request first runs: {config['pr_check']}")
    if config['protected']:
        lines.append('Changes to protected paths need human approval: ' + ', '.join(config['protected']))
    if config['human_merge']:
        lines.append('Merging pull requests is reserved for people.')
    print(json.dumps({'hookSpecificOutput': {'hookEventName': event, 'additionalContext': '\n'.join(lines)}}))


def handle_stop(root, payload, harness):
    config = load_config(root)
    path = state_path(root, payload)
    with locked(path):
        state = load_state(root, path)
        changed = changed_paths(root, state)
        if not changed:
            state['stop_blocks'] = 0
            save(path, state)
            return
        missing = missing_fields(payload.get('last_assistant_message'), config['receipt'])
        if missing and payload.get('hook_event_name') == 'SubagentStop':
            # Some harnesses deliver a subagent's report outside its last message.
            missing = missing_fields(subagent_report(payload), config['receipt'])
        if not missing:
            save(path, baseline(root))  # The receipt covers everything so far.
            return
        state['stop_blocks'] = state.get('stop_blocks', 0) + 1
        if state['stop_blocks'] > config['max_stop_blocks']:
            state['stop_blocks'] = 0
            save(path, state)
            if harness == 'claude':
                print(json.dumps({'systemMessage': 'Completion gate: the agent finished without a verification receipt.'}))
            return
        save(path, state)
    shown = ', '.join(changed[:10]) + (f' and {len(changed) - 10} more' if len(changed) > 10 else '')
    print(json.dumps({'decision': 'block', 'reason': (
        f"Completion gate: you changed {shown}, but your final message is missing {', '.join(missing)}. "
        'End with one line per field: ' + ' '.join(f'{f} <...>' for f in config['receipt']) + '. '
        'Report anything you could not verify under UNVERIFIED instead of omitting it.'
    )}))


def pr_actions(payload):
    tool = str(payload.get('tool_name', ''))
    tool_input = payload.get('tool_input')
    command = tool_input.get('command') if isinstance(tool_input, dict) else None
    if isinstance(command, list):
        command = ' '.join(map(str, command))
    command = command if isinstance(command, str) else ''
    actions = set()
    if MCP_CREATE.match(tool) or PR_CREATE.search(command):
        actions.add('create')
    if MCP_MERGE.match(tool) or PR_MERGE.search(command):
        actions.add('merge')
    return actions


def decide(harness, decision, reason):
    if decision == 'ask' and harness != 'claude':
        # Codex parses "ask" but fails open, so escalation becomes a denial.
        decision, reason = 'deny', 'Needs human approval. ' + reason + ' Ask the person to approve and run it.'
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': decision,
        'permissionDecisionReason': reason,
    }}))


def protected_changes(root, config):
    """Protected paths changed on this branch; None if no base branch resolves."""
    if not config['protected']:
        return []
    for ref in ([config['base_ref']] if config['base_ref'] else []) + list(BASE_REFS):
        result = git(root, 'merge-base', 'HEAD', ref, check=False)
        if result.returncode == 0:
            base = result.stdout.decode().strip()
            paths = names(git(root, 'diff', '--no-renames', '--name-only', '-z', base)) | dirty_paths(root)
            return sorted(p for p in paths if any(fnmatch.fnmatch(p, g) for g in config['protected']))
    return None


def tail(output, lines=40):
    return '\n'.join(output.decode(errors='replace').strip().splitlines()[-lines:])


def handle_pre_tool(root, payload, harness):
    actions = pr_actions(payload)
    if not actions:
        return
    config = load_config(root)
    reasons = []
    if 'create' in actions:
        if config['pr_check']:
            try:
                result = run(config['pr_check'], root, config['pr_check_timeout'], shell=True)
            except subprocess.TimeoutExpired:
                decide(harness, 'deny', f"Completion gate: `{config['pr_check']}` timed out; fix or report it before opening a pull request.")
                return
            if result.returncode:
                decide(harness, 'deny', (
                    f"Completion gate: `{config['pr_check']}` failed (exit {result.returncode}). "
                    'Fix the failures before opening a pull request; do not weaken checks.\n'
                    + tail(result.stdout + result.stderr)
                ))
                return
        protected = protected_changes(root, config)
        if protected is None:
            reasons.append('Completion gate: no base branch resolved, so protected paths could not be checked; set base_ref in the gate config.')
        elif protected:
            reasons.append('Completion gate: this change touches protected paths: ' + ', '.join(protected[:10]) + '.')
    if 'merge' in actions and config['human_merge']:
        reasons.append('Completion gate: merging pull requests is reserved for people.')
    if reasons:
        decide(harness, 'ask', ' '.join(reasons))


def main(argv):
    if argv == ['--self-test']:
        self_test()
        return 0
    harness = argv[1] if len(argv) == 2 and argv[0] == '--harness' else None
    if harness not in {'claude', 'codex'}:
        print('usage: gate.py --harness claude|codex | --self-test', file=sys.stderr)
        return 2
    payload = json.load(sys.stdin)
    event = payload.get('hook_event_name')
    try:
        root = repo_root(payload.get('cwd') or '.')
        if root is None:
            return 0
        if event in {'SessionStart', 'SubagentStart'}:
            handle_start(root, payload, event)
        elif event in {'Stop', 'SubagentStop'}:
            handle_stop(root, payload, harness)
        elif event == 'PreToolUse':
            handle_pre_tool(root, payload, harness)
        return 0
    except Exception as error:
        message = f'Completion gate error: {type(error).__name__}: {error}'
        print(message, file=sys.stderr)
        released = (
            event in {'SessionStart', 'SubagentStart'}
            or (event in {'Stop', 'SubagentStop'} and payload.get('stop_hook_active'))
            or (event == 'PreToolUse' and not pr_actions(payload))
        )
        return 0 if released else 2


def self_test():
    script = Path(__file__).resolve()
    safe = ['-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null']

    def hook(harness, payload):
        result = subprocess.run([sys.executable, '-I', str(script), '--harness', harness],
                                input=json.dumps(payload).encode(), capture_output=True, timeout=60)
        out = result.stdout.decode().strip()
        return result.returncode, (json.loads(out) if out else None), result.stderr.decode()

    def decision(harness, payload):
        out = hook(harness, payload)[1]
        return out and out['hookSpecificOutput']['permissionDecision']

    def new_repo(directory):
        root = Path(directory).resolve()
        for args in (['init', '-q'], ['symbolic-ref', 'HEAD', 'refs/heads/main'],
                     ['config', 'user.email', 'gate@example.com'], ['config', 'user.name', 'Gate']):
            git(root, *args)
        return root

    with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as scratch:
        root = new_repo(directory)
        (root / 'src').mkdir()
        (root / 'src/app.py').write_text('x = 0\n')
        (root / 'notes.txt').write_text('before\n')
        (root / 'specs').mkdir()
        (root / 'specs/login.feature').write_text('Feature: login\n')
        git(root, 'add', '.')
        git(root, *safe, 'commit', '-q', '-m', 'baseline')
        git(root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        (root / 'notes.txt').write_text('dirty before the session\n')
        base = {'session_id': 's1', 'cwd': str(root)}
        receipt = 'VERIFIED: tests\nUNVERIFIED: none\nPRECEDENT: none\nCONFIDENCE: high - tests pass'

        code, out, _ = hook('claude', {**base, 'hook_event_name': 'SessionStart', 'source': 'startup'})
        assert code == 0 and 'completion gate' in out['hookSpecificOutput']['additionalContext'], out
        stop = {**base, 'hook_event_name': 'Stop', 'stop_hook_active': False, 'last_assistant_message': 'done'}
        assert hook('claude', stop)[1] is None, 'no changes: pass'
        (root / 'notes.txt').write_text('dirty before the session\n')  # unchanged pre-existing dirt
        assert hook('codex', stop)[1] is None, 'pre-existing dirt is not attributed'
        (root / 'link').symlink_to('notes.txt')
        git(root, 'add', 'link')
        git(root, *safe, 'commit', '-q', '-m', 'link', '--', 'link')
        (root / 'link').unlink()
        (root / 'link').symlink_to('src/app.py')  # retargeted before the session
        hook('claude', {**base, 'hook_event_name': 'SessionStart', 'source': 'startup'})
        assert hook('claude', stop)[1] is None, 'unchanged dirty symlink is not attributed'
        (root / 'link').unlink()
        (root / 'link').symlink_to('specs/login.feature')
        assert 'link' in hook('claude', stop)[1]['reason'], 'retargeted symlink counts'

        (root / 'src/app.py').write_text('x = 1\n')  # as a shell command would
        out = hook('claude', stop)[1]
        assert out['decision'] == 'block' and 'src/app.py' in out['reason'], out
        partial = {**stop, 'last_assistant_message': 'UNVERIFIED: x\nPRECEDENT: y\nCONFIDENCE: low - z'}
        assert 'VERIFIED:' in hook('codex', partial)[1]['reason'], 'UNVERIFIED must not satisfy VERIFIED'
        assert hook('claude', {**stop, 'last_assistant_message': receipt})[1] is None, 'receipt passes'
        assert hook('claude', {**stop, 'last_assistant_message': 'It is 3pm.'})[1] is None, 'receipt re-baselines'

        (root / 'src/app.py').write_text('x = 2\n')
        git(root, *safe, 'commit', '-q', '-am', 'agent work')  # committed changes still count
        assert hook('claude', stop)[1]['decision'] == 'block', 'committed change counts'
        for _ in range(DEFAULTS['max_stop_blocks'] - 1):
            assert hook('claude', stop)[1]['decision'] == 'block'
        assert 'systemMessage' in hook('claude', stop)[1], 'block cap releases the agent'
        hook('claude', {**stop, 'last_assistant_message': receipt})

        sub = {**base, 'agent_id': 'a1'}
        hook('codex', {**sub, 'hook_event_name': 'SubagentStart'})
        transcript = Path(scratch) / 'agent.jsonl'
        (root / 'src/app.py').write_text('x = 3\n')
        sub_stop = {**sub, 'hook_event_name': 'SubagentStop', 'stop_hook_active': False,
                    'last_assistant_message': '', 'agent_transcript_path': str(transcript)}
        echoed = [{'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': receipt}]}},
                  {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'done, really'}]}}]
        transcript.write_text('\n'.join(map(json.dumps, echoed)) + '\n')
        assert hook('codex', sub_stop)[1]['decision'] == 'block', 'echoed receipt text does not count'
        handback = {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'name': 'SubagentHandback', 'input': {'message': receipt}}]}}
        transcript.write_text('\n'.join(map(json.dumps, echoed + [handback])) + '\n')
        assert hook('codex', sub_stop)[1] is None, 'handback report counts'

        pre = {**base, 'hook_event_name': 'PreToolUse', 'tool_name': 'Bash'}
        assert hook('claude', {**pre, 'tool_input': {'command': 'ls'}})[1] is None, 'unrelated tool passes'
        create = {**pre, 'tool_input': {'command': 'git push && gh pr create --fill'}}
        assert hook('claude', create)[1] is None, 'no config: creation allowed'
        config_dir = root / '.agents/gate'
        config_dir.mkdir(parents=True)
        config = {'pr_check': 'echo check-output; exit 3', 'protected': ['specs/*']}
        (config_dir / 'config.json').write_text(json.dumps(config))
        out = hook('codex', create)[1]['hookSpecificOutput']
        assert out['permissionDecision'] == 'deny' and 'check-output' in out['permissionDecisionReason'], out
        for command in ('gh pr new', 'gh -R o/r pr create', '/usr/bin/gh pr create', "bash -c 'gh pr create'",
                        'gh pr create && gh pr merge --auto'):
            assert decision('claude', {**pre, 'tool_input': {'command': command}}) == 'deny', command
        (config_dir / 'config.json').write_text(json.dumps({**config, 'pr_check': 'true'}))
        assert hook('claude', create)[1] is None, 'passing check, no protected change'
        git(root, 'mv', 'specs/login.feature', 'moved.feature')
        git(root, *safe, 'commit', '-q', '-m', 'rename spec', '--', 'specs/login.feature', 'moved.feature')
        out = hook('claude', create)[1]['hookSpecificOutput']
        assert out['permissionDecision'] == 'ask' and 'specs/login.feature' in out['permissionDecisionReason'], out
        out = hook('codex', create)[1]['hookSpecificOutput']
        assert out['permissionDecision'] == 'deny' and 'human approval' in out['permissionDecisionReason']
        git(root, 'update-ref', '-d', 'refs/remotes/origin/main')
        assert 'base branch' in hook('claude', create)[1]['hookSpecificOutput']['permissionDecisionReason']
        for tool in ('mcp__github__merge_pull_request', 'mcp__github__enable_pr_auto_merge'):
            assert decision('claude', {**pre, 'tool_name': tool, 'tool_input': {}}) == 'ask', tool

        (config_dir / 'config.json').write_text('{not json')
        assert hook('claude', stop)[0] == 2, 'gate errors fail closed'
        assert hook('claude', {**stop, 'stop_hook_active': True})[0] == 0, 'errors release after one retry'
        assert hook('claude', {**pre, 'tool_input': {'command': 'ls'}})[0] == 0, 'errors never block unrelated tools'

    with tempfile.TemporaryDirectory() as directory:
        root = new_repo(directory)
        empty = {'session_id': 's2', 'cwd': str(root)}
        hook('claude', {**empty, 'hook_event_name': 'SessionStart', 'source': 'startup'})
        (root / 'f.txt').write_text('new\n')
        git(root, 'add', '.')
        git(root, *safe, 'commit', '-q', '-m', 'first')
        out = hook('claude', {**empty, 'hook_event_name': 'Stop', 'last_assistant_message': 'done'})[1]
        assert out and 'f.txt' in out['reason'], 'first commit in a new repository counts'
    print('completion gate self-test passed')


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as error:  # Fail closed: exit 2 blocks Stop and PreToolUse.
        print(f'Completion gate error: {type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(2)
