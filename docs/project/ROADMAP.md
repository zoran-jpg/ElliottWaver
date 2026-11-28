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
- EP-DEF-11: Completed (accepted post-merge)
  - Scope covered: shared temporal domain and candle availability semantics.
  - Merge baseline: `f9431e0d83f3dead0f912926d817abff867a5206`
  - Accepted feature source: `e78b8118350b26ed4795597749fcef236be63e7a`
  - Accepted tree: `7cc8305111e6805a1495a7b77bc0892f137871bc`
  - Quality baseline: 466 passed, 92.73% coverage, feature CI 4/4, main CI 4/4.
- DEF-GOV-001: In progress
  - Scope: controlled synchronization of operational documentation before EP-DEF-12 implementation.
- EP-DEF-12: Architecture planning
  - Scope: temporal market data integration planning only, no implementation approval.
- EP-08+ and further strategic packages: Planned
  - To be activated only after explicit Product Owner approval.

## Planning notes

- Forecast/projection domain engines are considered stable and not part of active refactoring scope unless a verified engine defect appears.
- Roadmap V3.0 strategic goals, timelines, and time budgets remain unchanged.
- EP-DEF-11 closure does not imply complete causal look-ahead safety for the full production chain.
- Productive temporal market-data integration, causal pivot/swing and support/resistance integration, and downstream causal analysis integration remain pending explicit packages.
