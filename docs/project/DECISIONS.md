# Project decisions

## Document role

`DECISIONS.md` is the accepted decision index.
Each active decision links to an ADR when formalized.

## Active decision index

| ID | Title | Status | ADR |
| --- | --- | --- | --- |
| DEC-001 | Clean Architecture and DDD boundaries | Accepted | [docs/adr/0001-clean-architecture.md](docs/adr/0001-clean-architecture.md) |
| DEC-002 | Desktop controller/view separation | Accepted | [docs/adr/0002-desktop-controller-view-separation.md](docs/adr/0002-desktop-controller-view-separation.md) |
| DEC-003 | Worker-thread with queue and `after(...)` UI handoff | Accepted | [docs/adr/0003-desktop-thread-queue-after-model.md](docs/adr/0003-desktop-thread-queue-after-model.md) |
| DEC-004 | Immutable chart contract as rendering boundary | Accepted | [docs/adr/0004-chart-contract-and-rendering-boundary.md](docs/adr/0004-chart-contract-and-rendering-boundary.md) |
| DEC-005 | Constraints-driven dependency and packaging strategy | Accepted | [docs/adr/0005-dependency-ci-packaging-strategy.md](docs/adr/0005-dependency-ci-packaging-strategy.md) |
| DEC-006 | Python 3.12 runtime baseline | Accepted | ADR pending |
| DEC-007 | Hatchling build backend and src layout | Accepted | ADR pending |
| DEC-008 | Ruff for linting/formatting, MyPy for static typing | Accepted | ADR pending |
| DEC-009 | pytest + coverage gate (minimum 90%) | Accepted | ADR pending |
| DEC-010 | No automatic Copilot commits/pushes | Accepted | ADR pending |

## Governance notes

- `ELLIOTTWAVER_MASTER_CONTROL.md` remains the binding control baseline.
- Decisions are only marked accepted when reflected in repository code or process configuration.
- Open release status from EP-06 remains: GitHub Actions matrix execution is pending final release confirmation.

## Historical note

Earlier broad decision lists were consolidated into this active index to remove stale or duplicated entries while keeping accepted architecture intent intact.
