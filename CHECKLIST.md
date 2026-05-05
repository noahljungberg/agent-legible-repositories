# Agent-Legible Repository Checklist

## Entry And Routing

- [ ] `AGENTS.md` exists and is short enough to load every session.
- [ ] `AGENTS.md` links to architecture, conventions, design index, active plans, quality, and known issues.
- [ ] There is a clear session recovery workflow.
- [ ] There is one obvious current task source.

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
- [ ] Docs have status markers such as planned, in progress, complete, stale.

## Execution Plans

- [ ] Multi-step work lives in `docs/plans/active/`.
- [ ] Plans are checkable and ordered.
- [ ] Each task has acceptance criteria.
- [ ] Plans include decision and progress logs.
- [ ] Agents are told to stop after completing the requested task.

## Verification

- [ ] Build/test/lint commands are documented.
- [ ] Commands are wrapped in scripts when they are nontrivial.
- [ ] Tests mirror component boundaries.
- [ ] Domain-specific acceptance tests are documented.
- [ ] Verification is cheap enough to run often.

## Memory And Entropy

- [ ] `docs/QUALITY.md` records trust level by component.
- [ ] `known-issues.md` records non-blocking problems.
- [ ] Recurring mistakes are converted into docs, tests, lints, scripts, or skills.
- [ ] Stale docs can be detected by links, status, ownership, or review.

## Skills

- [ ] Repeated workflows have skills or playbooks.
- [ ] Skills are specific and hierarchical.
- [ ] Skills reference repo-local docs instead of duplicating everything.
- [ ] Skill output format is predictable.
