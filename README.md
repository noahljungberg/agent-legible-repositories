# Agent-Legible Repositories

A practical research note and reusable agent skill for designing repositories that AI coding agents can understand, modify, verify, and maintain.

I made this because I kept noticing that AI coding agents work much better in repositories where the documentation, architecture, plans, tests, and verification commands are designed as part of the engineering system.

This repo is my attempt to write down that pattern in a reusable way, so it can be fed to agents when creating new repositories or repairing old ones.

The central idea is simple:

> The repository is the agent interface.

Documentation, architecture rules, active plans, tests, scripts, and quality ledgers are not auxiliary material. They are the control surface through which coding agents perceive and change software systems.

## October 2026 Revision

When I wrote the first draft in May 2026, I mostly ran one agent at a time and still read the code it produced. That is no longer how I work. I routinely run ten or more agents against the same repository. I don't write code, and I rarely read it. I review intent and evidence instead.

Anthropic's [Redesigning source control at Anthropic](https://www.anthropic.com/engineering/redesigning-source-control) shows the same shift at much larger scale. Merged changes went from about 2,500 per day to over 30,000 per day in four months, and the bottleneck moved from writing code to infrastructure built for human scale: source control, builds, and CI. GitHub and Cursor have published similar accounts of rebuilding Git infrastructure for agent load. Anthropic built its own version control system. This repo does not suggest you do the same, and neither do they.

Git is still a bottleneck for this way of working, though. It isolates agents well, but it does not tell an agent what the other agents are doing, a checkout is stale as soon as it exists, and two changes can merge cleanly and still break together. Harnesses such as Claude Code and Codex already cover much of this gap. This revision adds the part the repository itself can own:

- Assume concurrency. Every agent should expect the repo to change underneath it.
- Make in-flight work visible with claims that declare scope.
- Shard files that every task appends to, and generate indices instead of hand-merging them.
- Verify the integrated result against the current trunk, not only the branch.
- Attach an intent record with evidence to every change, because that is what humans now review.

The paper adds a section on designing for concurrent agents. It also has an explicit evidence policy: because the field changes in months, recent first-party reports from Anthropic, OpenAI, and frontier AI-coding companies carry the argument, and older research is background. `SKILL.md` and `CHECKLIST.md` include the new rules.

### Gates instead of reading

If nobody reads the code, the constraints around it become the review. Robert C. Martin put it plainly: he does not read his agents' code; he surrounds them with tests, Gherkin scenarios, mutation testing, coverage, and quality metrics, and keeps function size and complexity tightly bounded because messy code slows agents down. I work the same way, with a personal gate enforced by hooks: an agent cannot finish without saying what it verified and what it did not, and cannot open a pull request until the checks pass.

The paper now has a section on gates, and [`templates/completion-gate/`](templates/completion-gate/) is a domain-neutral version of that gate for Claude Code and Codex. Repository skills belong in `.agents/skills/`, the cross-tool location, linked from `.claude/skills/` for Claude Code. This repository runs the same gate on itself: see the Completion Gate section of [`AGENTS.md`](AGENTS.md).

## Entry File Compatibility

This repo uses `AGENTS.md` as the generic name for the always-read agent entry file. In other tools or teams, the same role may be served by `CLAUDE.md`, `GEMINI.md`, Cursor rules, Copilot instructions, or another tool-specific file. The important idea is not the exact filename; it is that the repository has a short, maintained entry map that routes agents to the right deeper context.

## What This Contains

- [`paper/agent_legible_repositories.tex`](paper/agent_legible_repositories.tex) - cited LaTeX working paper.
- [`paper/references.bib`](paper/references.bib) - BibTeX references.
- [`SKILL.md`](SKILL.md) - operational skill distilled from the paper.
- [`CHECKLIST.md`](CHECKLIST.md) - quick audit checklist for greenfield and brownfield repositories.
- [`templates/completion-gate/`](templates/completion-gate/) - installable completion gate (hooks, config, and skill) for Claude Code and Codex.
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

To install `SKILL.md` as a skill, copy it to `.agents/skills/agent-legible-repositories/SKILL.md` in the target repository, or to your user-level skills folder.

To add a completion gate to a repository, run `templates/completion-gate/install.sh /path/to/repo` and read [`templates/completion-gate/README.md`](templates/completion-gate/README.md).

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
