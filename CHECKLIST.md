# Agent-Legible Repository Checklist

## Entry And Routing

- [ ] `AGENTS.md` exists and is short enough to load every session.
- [ ] `AGENTS.md` links to architecture, conventions, design index, active plans, quality, and known issues.
- [ ] `AGENTS.md` states the concurrency model: other agents may be editing, where in-flight work is visible, how to claim work.
- [ ] There is a clear session recovery workflow.
- [ ] There is one obvious source of task truth.

## Architecture And Conventions

- [ ] `ARCHITECTURE.md` defines layers or component boundaries.
- [ ] Dependency rules are explicit.
- [ ] Important dependency rules are mechanically checked.
- [ ] `CONVENTIONS.md` defines local patterns agents should copy.
- [ ] Error handling, logging, naming, tests, and comments are covered.

## Design Docs

- [ ] `docs/design/index.md` lists all major components.
- [ ] Each major component has one design doc, for example `docs/design/loader.md`, `docs/design/memory-reader.md`, `docs/design/overlay.md`, `docs/design/auth.md`, or `docs/design/billing.md`.
- [ ] Each component doc acts as a context router and lists public API, implementation files, dependencies, tests, constraints, and non-goals.
- [ ] Each component doc lists API consumers and shared or hub files.
- [ ] Docs have status markers such as planned, in progress, complete, stale.

## Execution Plans

- [ ] Multi-step work lives in `docs/plans/active/`, one file per task or workstream.
- [ ] Plans are checkable and ordered.
- [ ] Each task has acceptance criteria.
- [ ] Plans include decision and progress logs.
- [ ] Agents are told to stop after completing the requested task.

## Concurrency And Coordination

- [ ] There is one coordination surface: a shared harness task list, or claim headers in plan files.
- [ ] Claims record task, owner, start time, and scope (paths, interfaces, generated outputs).
- [ ] Agents check claims before starting and release them when work merges or is abandoned.
- [ ] Hub files and public contracts are identified, and changes to them are scheduled first.
- [ ] No single file must be appended to by every task. Indices, registries, and changelogs are generated.
- [ ] Lockfiles and generated code are regenerated, never hand-merged.
- [ ] Changes are small and integrate often. There are no long-lived branches by default.

## Verification

- [ ] Build/test/lint commands are documented.
- [ ] Commands are wrapped in scripts when they are nontrivial.
- [ ] Tests mirror component boundaries.
- [ ] Domain-specific acceptance tests are documented.
- [ ] Verification is cheap enough to run often. Output is short and greppable, and a fast mode exists.
- [ ] There is a documented way to verify a branch against the current trunk before declaring done.
- [ ] Post-merge checks catch semantic collisions between changes that each passed alone.

## Review And Intent

- [ ] Every change carries an intent record: intent, component, scope, non-goals, contract change, evidence, risk.
- [ ] Evidence points to checks a machine can re-run, not narrative assurances.
- [ ] Ownership or approval rules route sensitive changes (contracts, security, migrations) to human attention, and let low-risk changes through.
- [ ] Human rejections ("no") are encoded as lints, tests, non-goals, or anti-patterns.

## Memory And Entropy

- [ ] `docs/QUALITY.md` records trust level by component.
- [ ] Known issues record non-blocking problems, sharded per issue if many agents write to them.
- [ ] Recurring mistakes are converted into docs, tests, lints, scripts, or skills.
- [ ] Stale docs can be detected by links, status, ownership, or review.

## Skills

- [ ] Repeated workflows have skills or playbooks.
- [ ] Skills are specific and hierarchical.
- [ ] Skills reference repo-local docs instead of duplicating everything.
- [ ] Skill output format is predictable.
