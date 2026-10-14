# Skill: Agent-Legible Repository Design

Use this skill when creating, repairing, or auditing a repository so AI coding agents can implement most or all code with minimal wasted context and strong verification, including when many agents work in the repository at the same time.

## Goal

Make the repository navigable, bounded, verifiable, and self-documenting for future agents, and make concurrent agent work visible and composable. The repository is the agent interface.

## Core Principle

Do not feed agents one giant instruction blob. Give them a short map, indexed durable docs, component contracts, active plans, mechanical checks, and cheap verification commands.

Assume you are not alone. Other agents are probably changing the repository while you work. Treat what you read as a snapshot, declare what you will touch, and verify the integrated result, not only your branch.

## Entry File Compatibility

This skill uses `AGENTS.md` as the generic name for the agent entry map. If a target tool expects `CLAUDE.md`, `GEMINI.md`, Cursor rules, Copilot instructions, or another filename, use that file for the same purpose. The entry file should stay short and route agents to deeper docs.

## Required Artifacts

- `AGENTS.md`: short entry map that routes rather than lists: purpose, exact setup and verification commands, codebase gotchas, links to deeper docs, and the concurrency model (where in-flight work is visible, how to claim, how to verify against trunk). Do not make every edit read every doc first.
- `ARCHITECTURE.md`: layers, ownership boundaries, dependency rules, and rationale.
- `CONVENTIONS.md`: naming, error handling, logging, comments, tests, and local taste.
- `docs/design/index.md`: routing table for all design docs and their status.
- `docs/design/<component>.md`: one design doc per major component, such as `loader.md`, `memory-reader.md`, `overlay.md`, `auth.md`, `billing.md`, or `api.md`.
- `docs/plans/active/<task>.md`: one executable plan per task or workstream, with a claim header.
- `docs/decisions/<decision>.md`: one file per durable decision.
- `docs/QUALITY.md`: trust ledger for components, tests, docs, and risks.
- `docs/known-issues.md`: non-blocking debt and follow-up work. Use `docs/known-issues/`, one file per issue, when many agents write to it.
- `scripts/`: stable commands for one-line setup, build, test, lint, validation, generation, repair, and verifying a branch against the current trunk. Agents in fresh cloud environments only know what the repository says.
- `tests/`: verification harness aligned with component boundaries.
- Intent-record format: a short template for commit messages or pull request descriptions.
- Review rules: scoped rules in `AGENTS.md` (root for the repo, nested for services) for what a reviewer would otherwise have to ask. Keep formatting and other mechanical checks in CI.

## Greenfield Workflow

1. Write `AGENTS.md` first as a router, not an encyclopedia. Include the concurrency model.
2. Define architecture layers before many components exist.
3. Write conventions for the patterns agents are likely to copy.
4. Create `docs/design/index.md` before component docs multiply.
5. Add one component design doc before or alongside each major component, including owned paths and API consumers.
6. Add build/test/lint scripts early, plus a check against the current trunk, and document them in `AGENTS.md`.
7. Use one plan file per task for any task that spans more than one obvious edit.
8. Track quality, known issues, and decisions from the first nontrivial implementation, one entry per file where many agents write.
9. Define the intent-record format and scoped review rules.

## Brownfield Repair Workflow

1. Inventory the repo structure, build system, tests, scripts, and docs.
2. Create a short `AGENTS.md` that tells future agents where to start.
3. Create `ARCHITECTURE.md` from the actual code, then mark desired corrections.
4. Create `docs/design/index.md` with each component status: missing, stale, draft, complete.
5. Write component docs first for high-change, high-risk, confusing, or frequently edited areas.
6. Turn recurring manual commands into scripts.
7. Add mechanical checks for the most damaging recurring mistakes.
8. Add `docs/QUALITY.md` and known issues so agents know what is trustworthy.
9. If several agents already work here, find contention hotspots (files most often in conflicts or touched by unrelated changes) and shard, generate, or schedule them first.

## Component Design Docs

One major component should have one design doc. Examples: `docs/design/loader.md`, `docs/design/memory-reader.md`, `docs/design/overlay.md`, `docs/design/auth.md`, `docs/design/billing.md`, or `docs/design/api.md`.

These docs are context routers, not decoration. When an agent is asked to work on a component, it should read that component's design doc first instead of scanning the whole repository. If a component has no design doc, treat that as missing harness infrastructure.

They are also coordination boundaries. Assign parallel work by component, not by arbitrary file lists.

Each component design doc should include:

- Purpose: what this component owns.
- Public API: headers, exported functions/classes, CLI commands, schemas, routes, or events.
- Implementation files: file list and responsibility per file.
- Dependencies: allowed and forbidden imports or links.
- Consumers and shared files: who depends on the API, and which hub files changes here also touch.
- Constraints: performance, security, platform, file-size, error-handling, style.
- Tests: unit, integration, acceptance, fixtures, mocks.
- Non-goals: what future agents should not build here.
- Status: planned, in progress, complete, or needs update.

## Concurrency Rules

Git gives each agent isolation and a reliable merge. It does not show agents each other's intent, keep a checkout fresh, or prove that two clean merges still work together. Do not build a new version control system. Compensate in the repository:

- Assume a moving trunk. Re-read a file before editing it if time has passed. Treat earlier test results as stale once the trunk moves.
- Use one coordination surface. If agents share a harness task list with locked claiming, use it. Otherwise commit a claim header in the task's plan file: task, claimed-by, started, scope (paths, interfaces, generated outputs), status. Check claims before starting; amend when scope grows; release when merged or abandoned.
- Keep claims precise. Claims that are too broad serialize everything. Incomplete ones let agents collide anyway.
- Split parallel work along component and file boundaries. Schedule changes to public contracts and hub files; merge them first and record the affected consumers.
- Route expensive shared operations (full rebuilds, migrations, environment setup) through one owner instead of letting every agent trigger them.
- Shard shared knowledge. Avoid single files that every task appends to. Generate indices, registries, and changelogs with scripts. Regenerate lockfiles and generated code instead of hand-merging them.
- Keep changes small and short-lived. Integrate often. Split large agent changes into ordered stacks.
- Verify the integrated result. Before declaring done, sync with trunk, replay the merge, and re-run affected checks. Rely on post-merge, pre-deploy, and post-deploy checks for semantic collisions.
- Coordinate through durable, structured state (claims, contracts, intent records, checks), not free-form chat alone.

## Intent Records

Humans increasingly review intent and evidence instead of reading every line. Every change should carry:

- Intent: one sentence on what the change is for.
- Component: the component and contract it touches.
- Scope and non-goals: what changed, and what deliberately did not.
- Contract change: none, or the API change and its affected consumers.
- Checked: commands run against which trunk commit, with results. Point to evidence a machine or reviewer can re-check (tests, output, traces), not verdicts.
- Unverified: what could not be checked, and why. Never imply a check that did not run.
- Risk: low (docs, tests, comments), normal, or sensitive (public contracts, security, migrations), so human attention goes where it matters.

## Agent Task Protocol

When implementing a change in an agent-legible repo, scale the reading steps to the task; a typo fix does not need the full path:

1. Sync with the current trunk.
2. Read `AGENTS.md`.
3. Read the active plan or issue, and check existing claims for overlap.
4. Identify the target component through `docs/design/index.md`.
5. Claim the task with its expected scope, unless the harness already assigned it.
6. Read the component contract and relevant architecture/conventions.
7. Inspect existing code and tests in the target component.
8. Make the smallest change satisfying the task. Re-read files that others may have changed before editing them.
9. Run documented verification commands.
10. Re-sync with trunk, resolve conflicts, and re-run affected verification on the integrated result.
11. Write the intent record, including what remains unverified. Update plan/docs/quality only when durable project knowledge changed, and update instruction files in the same change that makes them outdated.
12. Release the claim and stop after the requested task is complete.

## Quality Rules

- Treat docs as executable context, not decoration.
- Prefer indexed Markdown over monolithic instructions.
- Prefer mechanical enforcement over prose-only rules. When humans stop reading code, nothing else catches drift.
- Prefer bounded task queues over broad autonomy.
- Prefer local examples and anti-patterns over abstract style advice.
- Convert repeated agent failures into docs, tests, lints, scripts, or skills.
- Fix the process, not the output. Encode every human "no" once, as a lint, test, rule, non-goal, or anti-pattern, so all concurrent agents inherit it. If the same mistake appears twice, add a check.
- For large tasks, define done as an executable check before implementation, so the standard cannot shrink to whatever was built.
- Keep verification output short and greppable. Put details in log files.
- Keep skills hierarchical with short descriptions; avoid large flat skill menus.

## Output When Auditing A Repo

Return:

1. Current agent-legibility grade.
2. Highest-impact missing artifacts.
3. Concurrency readiness: setup command, claim mechanism, contention hotspots, integration verification, intent-record format, review rules.
4. Concrete file creation/edit plan.
5. Mechanical checks to add.
6. Verification commands to standardize.
7. First three repairs to perform.
