# PROJECT_MANIFEST

## Purpose

`PROJECT_MANIFEST.md` is the stable constitutional document for ElliottWaver.
It defines architecture, engineering rules, quality expectations, and documentation responsibilities.

## Project Identity

- Project: ElliottWaver
- Type: Adaptive Market Decision Intelligence Platform
- Repository: `C:\Users\User\Desktop\ElliottWaver`
- Primary language: Python 3.12
- Build backend: Hatchling
- Package layout: src (`src/elliottwaver`)

## Product Goal

Deliver a maintainable and testable Elliott-Wave analysis platform with deterministic domain behavior, explicit application contracts, and reproducible quality gates.

## Architecture Constitution

- Clean Architecture and Domain-Driven Design are mandatory.
- Dependencies point inward.
- Domain code is independent from UI, infrastructure, and external systems.
- Interfaces call the application layer; infrastructure implements ports.
- Forecast and projection engines are not modified without proven engine defects.

## Dependency Rules

- `domain` must not depend on `application`, `interfaces`, `infrastructure`, or `bootstrap`.
- `application` orchestrates domain behavior and ports.
- `infrastructure` implements ports and adapter concerns.
- `interfaces` present application results and must not duplicate domain logic.

## Development Workflow

1. Inspect relevant docs and code before any package work.
2. Implement only the approved package scope.
3. Add/update deterministic tests for changed behavior.
4. Run full quality gates before completion claims.
5. Record exact evidence and residual risks in handover documentation.

## Quality Gates

Required before package completion:

- `python -m ruff format .`
- `python -m ruff check .`
- `python -m mypy src tests`
- `python -m pytest`
- `git status`

## Git Rules

- No Copilot commits or pushes unless explicitly requested.
- Never use destructive resets/restores on user changes.
- Protected test files must remain untouched:
  - `tests/unit/application/test_context_service.py`
  - `tests/unit/domain/context/test_elliott_context.py`

## Documentation Responsibilities

- `ELLIOTTWAVER_MASTER_CONTROL.md`: binding control baseline and package execution rules.
- `PROJECT_MANIFEST.md`: stable constitutional architecture and governance rules.
- `docs/project/status/CURRENT_STATUS.md`: verified operational snapshot only.
- `docs/project/ROADMAP.md`: planned and in-progress package progression.
- `docs/project/METRICS.md`: dated, reproducible quality measurements (with history).
- `docs/project/DECISIONS.md`: accepted decisions and ADR index.
- `engineering/HANDOVER.md`: package-specific evidence, tests, and residual risks.

## Governance Constraints

- Conflicts between docs must be reported and corrected explicitly.
- No unverified metrics or CI claims.
- Historical entries must remain labeled as historical.
- Package completion status is declared only after validation and user review.
