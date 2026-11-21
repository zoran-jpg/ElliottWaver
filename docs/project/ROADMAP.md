# Project roadmap

## Document role

`ROADMAP.md` captures planned and in-progress package progression.
It is a planning document, not a source of verified quality metrics.

## Operational package progression

- EP-DEF-01: Completed
  - Scope covered: productive analysis flow and CSV parsing centralization.
- EP-DEF-02: Completed
  - Scope covered: desktop responsiveness and controller/view responsibility split.
- EP-DEF-03: Completed (local verification)
  - Scope covered: packaging and CI release gates.
  - Open gate: real GitHub Actions matrix execution remains pending.
- EP-DEF-04: Completed
  - Scope covered: interface boundary hardening and test quality improvements.
- EP-DEF-05: Completed
  - Scope covered: governance/documentation foundations.
- EP-DEF-06: Completed
  - Scope covered: interpreter-bound pip usage, constraints-based reproducibility, Ruff-only formatter strategy.
- EP-07: In progress
  - Scope: CHART-004 + DEF-001 + DEF-014.
- EP-08+: Planned
  - To be activated only after explicit Product Owner approval.

## Planning notes

- Forecast/projection domain engines are considered stable and not part of active refactoring scope unless a verified engine defect appears.
- Release readiness depends on successful execution of the open GitHub Actions matrix gate in addition to local gates.
