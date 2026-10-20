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
Any internal error exits 2, which blocks Stop and PreToolUse in both harnesses.
"""
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tempfile
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
    'human_merge': True,
    'max_stop_blocks': 3,
}
PR_CREATE = re.compile(r'(^|[\s;&|(])gh\s+pr\s+create\b')
PR_MERGE = re.compile(r'(^|[\s;&|(])gh\s+pr\s+merge\b')
MCP_CREATE = re.compile(r'^mcp__.+__create_pull_request$')
MCP_MERGE = re.compile(r'^mcp__.+__merge_pull_request$')
BASE_REFS = ('origin/HEAD', 'origin/main', 'origin/master')


def run(args, cwd, timeout=30, shell=False):
    return subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, shell=shell)


def git(root, *args, check=True):
    result = run(['git', *args], root)
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
    paths = names(git(root, 'diff', '--name-only', '-z'))
    paths |= names(git(root, 'diff', '--cached', '--name-only', '-z'))
    return paths | names(git(root, 'ls-files', '--others', '--exclude-standard', '-z'))


def digest(data):
    return None if data is None else hashlib.sha256(data).hexdigest()


def file_digest(root, path):
    target = root / path
    return digest(target.read_bytes()) if target.is_file() else None


def load_config(root):
    path = root / CONFIG_PATH
    config = dict(DEFAULTS)
    if path.is_file():
        config.update(json.loads(path.read_text(encoding='utf8')))
    return config


# State: one file per (worktree, session, agent) inside the git common dir,
# so it is never committed and parallel agents never share a baseline.

def state_path(root, payload):
    common = Path(git(root, 'rev-parse', '--git-common-dir').stdout.decode().strip())
    directory = (common if common.is_absolute() else root / common) / 'agent-gate'
    identity = f"{root}:{payload.get('session_id', 'unknown')}:{payload.get('agent_id') or 'main'}"
    return directory / f'{hashlib.sha256(identity.encode()).hexdigest()}.json'


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


def baseline(root):
    return {
        'head': head(root),
        'digests': {path: file_digest(root, path) for path in dirty_paths(root)},
        'stop_blocks': 0,
    }


def load_state(root, path):
    if path.is_file():
        return json.loads(path.read_text(encoding='utf8'))
    # No baseline (hooks installed mid-session): judge everything since HEAD.
    return {'head': head(root), 'digests': {}, 'stop_blocks': 0}


def baseline_digest(root, state, path):
    if path in state['digests']:
        return state['digests'][path]
    if not state['head']:
        return None
    result = git(root, 'show', f"{state['head']}:{path}", check=False)
    return digest(result.stdout) if result.returncode == 0 else None


def changed_paths(root, state):
    """Paths whose content differs from the session baseline.

    Compares the whole tree, so edits made through shell commands and commits
    count. In a checkout shared with other agents, their edits count too.
    """
    candidates = dirty_paths(root) | set(state['digests'])
    current = head(root)
    if state['head'] and current and current != state['head']:
        candidates |= names(git(root, 'diff', '--name-only', '-z', state['head'], current))
    return sorted(p for p in candidates if baseline_digest(root, state, p) != file_digest(root, p))


def missing_fields(text, fields):
    # A field counts only as a whole word followed by a value on the same line,
    # so "UNVERIFIED: x" does not satisfy "VERIFIED:".
    return [f for f in fields if not re.search(r'(?<![A-Za-z])' + re.escape(f) + r'[ \t]*\S', text or '')]


def transcript_tail(payload):
    path = payload.get('agent_transcript_path') or payload.get('transcript_path')
    if not path or not Path(path).is_file():
        return ''
    data = Path(path).read_bytes()[-20000:]
    return data.decode(errors='replace').replace('\\n', '\n')


def handle_start(root, payload, harness, event):
    path = state_path(root, payload)
    with locked(path):
        if event == 'SubagentStart' or payload.get('source') in {'startup', 'clear'} or not path.exists():
            save(path, baseline(root))
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
        text = payload.get('last_assistant_message') or ''
        missing = missing_fields(text, config['receipt'])
        if missing and payload.get('hook_event_name') == 'SubagentStop':
            # Some harnesses deliver a subagent's report outside its last message.
            missing = missing_fields(transcript_tail(payload), config['receipt'])
        if not changed or not missing:
            state['stop_blocks'] = 0
            save(path, state)
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


def pr_action(payload):
    tool = str(payload.get('tool_name', ''))
    tool_input = payload.get('tool_input')
    command = tool_input.get('command') if isinstance(tool_input, dict) else None
    if isinstance(command, list):
        command = ' '.join(map(str, command))
    command = command if isinstance(command, str) else ''
    if MCP_MERGE.match(tool) or PR_MERGE.search(command):
        return 'merge'
    if MCP_CREATE.match(tool) or PR_CREATE.search(command):
        return 'create'
    return None


def decide(harness, decision, reason):
    if decision == 'ask' and harness != 'claude':
        # Codex parses "ask" but fails open, so escalation becomes a denial.
        decision, reason = 'deny', 'Needs human approval. ' + reason + ' Ask the person to approve and run it.'
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': decision,
        'permissionDecisionReason': reason,
    }}))


def branch_changes(root):
    for ref in BASE_REFS:
        result = git(root, 'merge-base', 'HEAD', ref, check=False)
        if result.returncode == 0:
            base = result.stdout.decode().strip()
            return names(git(root, 'diff', '--name-only', '-z', base)) | dirty_paths(root)
    return dirty_paths(root)


def tail(output, lines=40):
    return '\n'.join(output.decode(errors='replace').strip().splitlines()[-lines:])


def handle_pre_tool(root, payload, harness):
    action = pr_action(payload)
    if action is None:
        return
    config = load_config(root)
    if action == 'merge':
        if config['human_merge']:
            decide(harness, 'ask', 'Completion gate: merging pull requests is reserved for people.')
        return
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
    protected = sorted(p for p in branch_changes(root) if any(fnmatch.fnmatch(p, g) for g in config['protected']))
    if protected:
        decide(harness, 'ask', 'Completion gate: this change touches protected paths: ' + ', '.join(protected[:10]) + '.')


def main(argv):
    if argv == ['--self-test']:
        self_test()
        return 0
    harness = argv[1] if len(argv) == 2 and argv[0] == '--harness' else None
    if harness not in {'claude', 'codex'}:
        print('usage: gate.py --harness claude|codex | --self-test', file=sys.stderr)
        return 2
    payload = json.load(sys.stdin)
    root = repo_root(payload.get('cwd') or '.')
    if root is None:
        return 0
    event = payload.get('hook_event_name')
    if event in {'SessionStart', 'SubagentStart'}:
        handle_start(root, payload, harness, event)
    elif event in {'Stop', 'SubagentStop'}:
        handle_stop(root, payload, harness)
    elif event == 'PreToolUse':
        handle_pre_tool(root, payload, harness)
    return 0


def self_test():
    script = Path(__file__).resolve()

    def hook(harness, payload):
        result = subprocess.run([sys.executable, '-I', str(script), '--harness', harness],
                                input=json.dumps(payload).encode(), capture_output=True, timeout=60)
        out = result.stdout.decode().strip()
        return result.returncode, (json.loads(out) if out else None), result.stderr.decode()

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        for args in (['init', '-q', '-b', 'main'], ['config', 'user.email', 'gate@example.com'],
                     ['config', 'user.name', 'Gate']):
            git(root, *args)
        (root / 'src').mkdir()
        (root / 'src/app.py').write_text('x = 0\n')
        (root / 'notes.txt').write_text('before\n')
        (root / 'specs').mkdir()
        (root / 'specs/login.feature').write_text('Feature: login\n')
        git(root, 'add', '.')
        git(root, 'commit', '-q', '-m', 'baseline')
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

        (root / 'src/app.py').write_text('x = 1\n')  # as a shell command would
        code, out, _ = hook('claude', stop)
        assert out['decision'] == 'block' and 'src/app.py' in out['reason'], out
        partial = {**stop, 'last_assistant_message': 'UNVERIFIED: x\nPRECEDENT: y\nCONFIDENCE: low - z'}
        assert 'VERIFIED:' in hook('codex', partial)[1]['reason'], 'UNVERIFIED must not satisfy VERIFIED'
        assert hook('claude', {**stop, 'last_assistant_message': receipt})[1] is None, 'receipt passes'

        git(root, 'commit', '-q', '-am', 'agent work')  # committed changes still count
        assert hook('claude', stop)[1]['decision'] == 'block', 'committed change counts'
        for _ in range(DEFAULTS['max_stop_blocks'] - 1):
            assert hook('claude', stop)[1]['decision'] == 'block'
        assert 'systemMessage' in hook('claude', stop)[1], 'block cap releases the agent'

        sub = {**base, 'agent_id': 'a1'}
        hook('codex', {**sub, 'hook_event_name': 'SubagentStart'})
        transcript = Path(tempfile.mkdtemp()) / 'agent.jsonl'
        transcript.write_text(json.dumps({'tool_input': {'message': receipt}}) + '\n')
        (root / 'src/app.py').write_text('x = 2\n')
        sub_stop = {**sub, 'hook_event_name': 'SubagentStop', 'last_assistant_message': '',
                    'agent_transcript_path': str(transcript)}
        assert hook('codex', sub_stop)[1] is None, 'subagent report found in transcript'
        transcript.unlink()
        transcript.parent.rmdir()

        pre = {**base, 'hook_event_name': 'PreToolUse', 'tool_name': 'Bash'}
        assert hook('claude', {**pre, 'tool_input': {'command': 'ls'}})[1] is None, 'unrelated tool passes'
        create = {**pre, 'tool_input': {'command': 'git push && gh pr create --fill'}}
        assert hook('claude', create)[1] is None, 'no config: creation allowed'
        config_dir = root / '.agents/gate'
        config_dir.mkdir(parents=True)
        config = {'pr_check': 'echo check-output; exit 3', 'protected': ['specs/*']}
        (config_dir / 'config.json').write_text(json.dumps(config))
        decision = hook('codex', create)[1]['hookSpecificOutput']
        assert decision['permissionDecision'] == 'deny' and 'check-output' in decision['permissionDecisionReason'], decision
        (config_dir / 'config.json').write_text(json.dumps({**config, 'pr_check': 'true'}))
        assert hook('claude', create)[1] is None, 'passing check, no protected change'
        (root / 'specs/login.feature').write_text('Feature: login, weakened\n')
        decision = hook('claude', create)[1]['hookSpecificOutput']
        assert decision['permissionDecision'] == 'ask' and 'specs/login.feature' in decision['permissionDecisionReason']
        decision = hook('codex', create)[1]['hookSpecificOutput']
        assert decision['permissionDecision'] == 'deny' and 'human approval' in decision['permissionDecisionReason']
        merge = {**pre, 'tool_name': 'mcp__github__merge_pull_request', 'tool_input': {'pullNumber': 1}}
        assert hook('claude', merge)[1]['hookSpecificOutput']['permissionDecision'] == 'ask'

        (config_dir / 'config.json').write_text('{not json')
        code, _, err = hook('claude', stop)
        assert code == 2 and err, 'guard errors fail closed'
    print('completion gate self-test passed')


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as error:  # Fail closed: exit 2 blocks Stop and PreToolUse.
        print(f'Completion gate error: {type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(2)
