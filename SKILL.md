# Skill: Agent-Legible Repository Design

Use this skill when creating, repairing, or auditing a repository so AI coding agents can implement most or all code with minimal wasted context and strong verification.

## Goal

Make the repository navigable, bounded, verifiable, and self-documenting for future agents. The repository is the agent interface.

## Core Principle

Do not feed agents one giant instruction blob. Give them a short map, indexed durable docs, component contracts, active plans, mechanical checks, and cheap verification commands.

## Entry File Compatibility

This skill uses `AGENTS.md` as the generic name for the agent entry map. If a target tool expects `CLAUDE.md`, `GEMINI.md`, Cursor rules, Copilot instructions, or another filename, use that file for the same purpose. The entry file should stay short and route agents to deeper docs.

## Required Artifacts

- `AGENTS.md`: short entry map with purpose, workflow, commands, and links to deeper docs.
- `ARCHITECTURE.md`: layers, ownership boundaries, dependency rules, and rationale.
- `CONVENTIONS.md`: naming, error handling, logging, comments, tests, and local taste.
- `docs/design/index.md`: routing table for all design docs and their status.
- `docs/design/<component>.md`: one component contract per major component.
- `docs/plans/active/*.md`: executable task plans for multi-step work.
- `docs/QUALITY.md`: trust ledger for components, tests, docs, and risks.
- `docs/plans/known-issues.md`: non-blocking debt and follow-up work.
- `scripts/`: stable commands for build, test, lint, validation, generation, and repair.
- `tests/`: verification harness aligned with component boundaries.

## Greenfield Workflow

1. Write `AGENTS.md` first as a router, not an encyclopedia.
2. Define architecture layers before many components exist.
3. Write conventions for the patterns agents are likely to copy.
4. Create `docs/design/index.md` before component docs multiply.
5. Add a component contract before or alongside each component.
6. Add build/test/lint scripts early and document them in `AGENTS.md`.
7. Use active plans for any task that spans more than one obvious edit.
8. Track quality and known issues from the first nontrivial implementation.

## Brownfield Repair Workflow

1. Inventory the repo structure, build system, tests, scripts, and docs.
2. Create a short `AGENTS.md` that tells future agents where to start.
3. Create `ARCHITECTURE.md` from the actual code, then mark desired corrections.
4. Create `docs/design/index.md` with each component status: missing, stale, draft, complete.
5. Write component docs first for high-change, high-risk, or confusing areas.
6. Turn recurring manual commands into scripts.
7. Add mechanical checks for the most damaging recurring mistakes.
8. Add `docs/QUALITY.md` and `known-issues.md` so agents know what is trustworthy.

## Component Contract Template

Each component design doc should include:

- Purpose: what this component owns.
- Public API: headers, exported functions/classes, CLI commands, schemas, routes, or events.
- Implementation files: file list and responsibility per file.
- Dependencies: allowed and forbidden imports or links.
- Constraints: performance, security, platform, file-size, error-handling, style.
- Tests: unit, integration, acceptance, fixtures, mocks.
- Non-goals: what future agents should not build here.
- Status: planned, in progress, complete, or needs update.

## Agent Task Protocol

When implementing a change in an agent-legible repo:

1. Read `AGENTS.md`.
2. Read the active plan or issue.
3. Identify the target component through `docs/design/index.md`.
4. Read the component contract and relevant architecture/conventions.
5. Inspect existing code and tests in the target component.
6. Make the smallest change satisfying the task.
7. Run documented verification commands.
8. Update plan/docs/quality only when durable project knowledge changed.
9. Stop after the requested task is complete.

## Quality Rules

- Treat docs as executable context, not decoration.
- Prefer indexed Markdown over monolithic instructions.
- Prefer mechanical enforcement over prose-only rules.
- Prefer bounded task queues over broad autonomy.
- Prefer local examples and anti-patterns over abstract style advice.
- Convert repeated agent failures into docs, tests, lints, scripts, or skills.
- Keep skills hierarchical; avoid large flat skill menus.

## Output When Auditing A Repo

Return:

1. Current agent-legibility grade.
2. Highest-impact missing artifacts.
3. Concrete file creation/edit plan.
4. Mechanical checks to add.
5. Verification commands to standardize.
6. First three repairs to perform.
