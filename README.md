# Agent-Legible Repositories

A practical research note and reusable agent skill for designing repositories that AI coding agents can understand, modify, verify, and maintain.

I made this because I kept noticing that AI coding agents work much better in repositories where the documentation, architecture, plans, tests, and verification commands are designed as part of the engineering system.

This repo is my attempt to write down that pattern in a reusable way, so it can be fed to agents when creating new repositories or repairing old ones.

The central idea is simple:

> The repository is the agent interface.

Documentation, architecture rules, active plans, tests, scripts, and quality ledgers are not auxiliary material. They are the control surface through which coding agents perceive and change software systems.

## Entry File Compatibility

This repo uses `AGENTS.md` as the generic name for the always-read agent entry file. In other tools or teams, the same role may be served by `CLAUDE.md`, `GEMINI.md`, Cursor rules, Copilot instructions, or another tool-specific file. The important idea is not the exact filename; it is that the repository has a short, maintained entry map that routes agents to the right deeper context.

## What This Contains

- [`paper/agent_legible_repositories.tex`](paper/agent_legible_repositories.tex) - cited LaTeX working paper.
- [`paper/references.bib`](paper/references.bib) - BibTeX references.
- [`SKILL.md`](SKILL.md) - operational skill distilled from the paper.
- [`CHECKLIST.md`](CHECKLIST.md) - quick audit checklist for greenfield and brownfield repositories.
- [`AGENTS.md`](AGENTS.md) - instructions for future coding agents working on this repo.

## Who This Is For

This repository is for people using AI coding agents to create, repair, or maintain software repositories. It is especially useful when you want most implementation work to be done by agents, but you still want the resulting codebase to stay coherent over time.

## How To Use It

For practical repo work, feed an agent [`SKILL.md`](SKILL.md) and ask it to audit or repair a target repository.

For deeper context, feed the agent the paper:

```text
paper/agent_legible_repositories.tex
paper/references.bib
```

For a quick human or agent audit, use [`CHECKLIST.md`](CHECKLIST.md).

## Build The Paper

If you have a LaTeX environment installed:

```bash
make paper
```

The generated PDF will be written under `paper/`.

GitHub Actions also builds the paper on every push and uploads the PDF as a workflow artifact.

## Repository

Public repository URL:

```text
https://github.com/noahljungberg/agent-legible-repositories
```

## Citation

Use [`CITATION.cff`](CITATION.cff) or cite the paper source directly. The paper is a working synthesis intended to evolve as agent tooling and research change.

## License

This work is released under the Creative Commons Attribution 4.0 International License. See [`LICENSE`](LICENSE).
