# AGENTS.md - Agent-Legible Repositories

## Purpose

This repository contains a research paper, bibliography, checklist, and reusable skill for designing repositories that AI coding agents can navigate and maintain.

## Source Of Truth

- Paper: `paper/agent_legible_repositories.tex`
- Bibliography: `paper/references.bib`
- Operational skill: `SKILL.md`
- Audit checklist: `CHECKLIST.md`
- Build workflow: `.github/workflows/build-paper.yml`

## Workflow For Agents

1. Read this file and the user request.
2. If editing the research argument, update the paper first and then update `SKILL.md` or `CHECKLIST.md` only if the operational guidance changes.
3. If adding or changing citations, update both `paper/references.bib` and the relevant `\cite{...}` references in the paper.
4. Keep the project domain-neutral. Do not cite private repositories, private chats, or implementation-specific case studies unless the user explicitly asks.
5. Prefer concise, durable wording. The main consumer is often another AI agent.
6. Run `make paper` when a LaTeX toolchain is available. If it is not available, state that clearly.

## Public-Repo Hygiene

- Do not add private project names, local paths, secrets, tokens, or machine-specific details.
- Do not vendor generated LaTeX auxiliary files.
- Keep `SKILL.md` directly actionable and shorter than the paper.
- Keep `CHECKLIST.md` scannable.

## Verification

```bash
make paper
```

If LaTeX is unavailable locally, rely on the GitHub Actions workflow after pushing.
