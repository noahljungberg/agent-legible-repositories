# AGENTS.md - Agent-Legible Repositories

## Purpose

This repository contains a research paper, bibliography, checklist, and reusable skill for designing repositories that AI coding agents can navigate and maintain.

## Source Of Truth

- Paper: `paper/agent_legible_repositories.tex`
- Bibliography: `paper/references.bib`
- Operational skill: `SKILL.md`
- Audit checklist: `CHECKLIST.md`
- Build workflow: `.github/workflows/build-paper.yml`
- Completion gate template: `templates/completion-gate/` (keep it domain-neutral and dependency-free)

## Workflow For Agents

1. Read this file and the user request.
2. If editing the research argument, update the paper first and then update `SKILL.md` or `CHECKLIST.md` only if the operational guidance changes.
3. If adding or changing citations, update both `paper/references.bib` and the relevant `\cite{...}` references in the paper.
4. Keep the project domain-neutral. Do not cite private repositories, private chats, or implementation-specific case studies unless the user explicitly asks.
5. Prefer concise, durable wording. The main consumer is often another AI agent.
6. Run `make paper` when a LaTeX toolchain is available. If it is not available, state that clearly.

## Source Weighting

The field changes in months. When adding or weighing sources, follow the paper's Evidence Policy section:

- Recency first. Sources from roughly the last quarter before the revision carry the argument. Older sources are background only; no recommendation should rest on them alone.
- Frontier practice second. Prefer first-party engineering reports and docs from Anthropic, OpenAI, and AI-coding companies and forges running current agents at scale, over academic preprints. Recent preprints count as corroboration.
- Verify every source before citing it: confirm the publication date on the page and copy quotes exactly. Do not cite anything you could not open.
- Record an access date in each new `references.bib` entry.
- On each revision, re-run the search and move sources that have aged out into the paper's background section.

## Concurrency

Other agents may be editing this repository at the same time.

- Pull the latest branch before editing and again before committing.
- Keep each change scoped to the sections or files the task needs. Avoid reflowing or reordering text you did not need to change.
- Re-read a file before editing it if time has passed since you last read it.
- Add new references to the end of `paper/references.bib` to keep merges simple.

## Completion Gate

This repository runs its own completion gate: `.agents/gate/` (the script links to `templates/completion-gate/gate.py`), with hooks in `.claude/settings.json` and `.codex/hooks.json`. Load the `completion-gate` skill before changing files.

- If you change files, end your final message with `VERIFIED:`, `UNVERIFIED:`, `PRECEDENT:`, and `CONFIDENCE:` lines. Put anything you could not run, such as the paper build without LaTeX, under `UNVERIFIED`.
- Opening a pull request runs `make check` first.
- Changes to the gate, the hooks, `scripts/check_repo.py`, or CI workflows need human approval.
- Repository skills live in `.agents/skills/`, linked from `.claude/skills/`.

## Public-Repo Hygiene

- Do not add private project names, local paths, secrets, tokens, or machine-specific details.
- Do not vendor generated LaTeX auxiliary files.
- Keep `SKILL.md` directly actionable and shorter than the paper.
- Keep `CHECKLIST.md` scannable.

## Verification

```bash
make check
```

`make check` runs the gate self-test and `scripts/check_repo.py` (citations, access dates, committed files), and builds the paper when LaTeX is available.

If LaTeX is unavailable locally, rely on the GitHub Actions workflow after pushing.
