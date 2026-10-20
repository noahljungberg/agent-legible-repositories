# Completion Gate

A small, dependency-free gate for coding agents running in Claude Code or Codex. It turns "done" into something an agent cannot skip:

- **End of turn.** An agent that changed files cannot finish until its final message has a verification receipt:

  ```text
  VERIFIED: <commands and product surfaces that passed>
  UNVERIFIED: <anything not exercised and why, or none>
  PRECEDENT: <commits or pull requests checked when changing existing behavior, or none>
  CONFIDENCE: <low|medium|high> - <evidence-based reason>
  ```

- **Before a pull request.** Creating a pull request (`gh pr create` or `gh pr new`, including `gh -R owner/repo ...` forms, or an MCP `*_create_pull_request*` tool) first runs the repository's full check and is denied if it fails. Changes to protected paths, such as human-approved acceptance specs, escalate to a person, including renames and changes already committed on the branch.
- **Merges stay with people.** `gh pr merge` and MCP `*_merge_pull_request` or `*_enable_pr_auto_merge` calls escalate to a person.

The gate is the floor, not proof that the product works. The `completion-gate` skill carries the workflow: reproduce, check precedent in git history, fix the root cause, verify on the real surface, use a fresh reviewer, and finish with the receipt.

## Install

From a clone of this repository:

```bash
templates/completion-gate/install.sh /path/to/your/repo
```

The installer never overwrites files. It adds:

| Path | Purpose |
| --- | --- |
| `.agents/gate/gate.py` | Hook script for both harnesses |
| `.agents/gate/config.json` | Gate configuration |
| `.agents/skills/completion-gate/` | Workflow skill (Agent Skills format, plus `agents/openai.yaml` for Codex) |
| `.claude/skills/completion-gate` | Link to the skill for Claude Code |
| `.claude/settings.json` | Claude Code hooks |
| `.codex/hooks.json` | Codex hooks |

If `.claude/settings.json` or `.codex/hooks.json` already exists, the installer skips it; merge the `hooks` entries from `claude-settings.json` or `codex-hooks.json` by hand. Then edit the configuration and commit everything.

Trust: Claude Code loads project hooks after you accept the workspace trust dialog. Codex loads project hooks only for trusted projects and asks you to review each new or changed hook in `/hooks`.

## Configure

`.agents/gate/config.json`:

| Key | Default | Meaning |
| --- | --- | --- |
| `receipt` | the four fields above | Fields the final message must contain, each followed by a value |
| `pr_check` | `null` | Shell command run from the repository root before a pull request is created, for example `make check` |
| `pr_check_timeout` | `540` | Seconds before the check counts as failed; keep it below the hook timeout (600) |
| `protected` | `[]` | Glob patterns, such as `"features/*"`; `*` also matches `/` |
| `base_ref` | `null` | Branch to diff against for protected paths; otherwise `origin/HEAD`, `origin/main`, then `origin/master`. If none resolves, pull request creation escalates |
| `human_merge` | `true` | Escalate merges to a person |
| `max_stop_blocks` | `3` | Consecutive end-of-turn blocks before the agent is released with a warning |

Put the repository's real verification in `pr_check`: format, lint, typecheck, tests, mutation testing on changed code, coverage and complexity budgets. Keep the end-of-turn gate cheap; it only checks the receipt.

## Behavior

- **Attribution.** At session or subagent start, the gate records the commit and the blob ids of already-modified files under `.git/agent-gate/` (state older than 14 days is pruned). At the end of the turn it compares the whole working tree with that baseline, so edits made through shell commands, commits, and renames count. In a checkout shared with other agents, their edits count too. That is a cheap false positive (write the receipt) rather than a silent false negative. Give each agent its own worktree when you can.
- **Receipts.** Each field must appear as a whole word with a value, so `UNVERIFIED:` does not satisfy `VERIFIED:`. A passing receipt moves the baseline forward, so later turns without new changes need no receipt. For subagents whose report is delivered by a handback tool rather than their last message, the gate also reads the last assistant-authored content in the subagent transcript; tool results and hook feedback never count.
- **Escalation.** Claude Code supports asking a person before a tool call runs, so protected changes and merges prompt for approval. Codex does not support that yet and would let the call through, so on Codex the gate denies instead and tells the agent to ask the person.
- **Loops.** After `max_stop_blocks` consecutive blocks the agent is released (Claude Code also shows a warning).
- **Errors.** An internal error exits with status 2, which blocks pull request creation and stopping. A stop that already retried once is released, and unrelated tool calls are never blocked, so a broken gate cannot trap a session.
- **Missing script.** If `.agents/gate/gate.py` does not exist, for example while an older commit is checked out, the hooks do nothing.

## Limits

- The receipt check verifies that fields are present, not that they are true. CI, branch protection, and fresh reviewers still need to check the claims.
- Hooks are fast feedback, not a security boundary. Repeat important checks in CI.
- Pull request detection is pattern-based. Raw API calls, other CLIs, and aliases are not intercepted. Text that merely mentions `gh pr create`, such as a commit message, can trigger the check; that errs on the safe side.
- If `python3` is missing or a hook cannot start, both harnesses let the action through. CI is the boundary that does not depend on the agent's machine.
- POSIX file locking is used when available; on Windows, state writes are atomic but not locked.

## Personal gates

The repository's `AGENTS.md` and this gate define what is true for every contributor. A person can add a stricter personal gate in their user-level hooks and skills, with repository-specific variants that route to each repository's exact commands, as long as it adds to the repository's instructions and never overrides them.

## Test

```bash
python3 -I templates/completion-gate/gate.py --self-test
```

The self-test simulates both harnesses against a temporary repository.
