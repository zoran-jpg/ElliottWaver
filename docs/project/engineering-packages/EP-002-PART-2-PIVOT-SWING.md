# EP-002 Part 2 – Pivot & Swing Domain Model

Status: Implementation in progress

## Background

This engineering package adds foundational domain models for market Pivots and
Swings. It focuses on domain modeling and unit tests only; it does not include
wave-detection, Fibonacci logic, application services, or infrastructure.

## Goal

Define `PivotType`, `Pivot`, `SwingDirection`, and `Swing` domain types with
strict invariants and comprehensive unit tests.

## Scope

Included:
- Domain models under `src/elliottwaver/domain/market/`
- Unit tests under `tests/unit/domain/market/`
- Engineering Package documentation update

Excluded:
- Detection algorithms
- Application services or infrastructure
- Commits or pushes

## Inspected files
- PROJECT_MANIFEST.md
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- docs/project/DECISIONS.md
- docs/project/METRICS.md
- docs/project/prompts/ENGINEERING_PACKAGE_TEMPLATE.md
- .github/copilot-instructions.md
- .github/instructions/domain.instructions.md
- .github/instructions/tests.instructions.md
- pyproject.toml
- src/elliottwaver/core/shared/
- src/elliottwaver/core/market/
- src/elliottwaver/domain/market/
- tests/unit/domain/market/

## Created files
- src/elliottwaver/domain/market/pivot.py
- src/elliottwaver/domain/market/swing.py
- tests/unit/domain/market/test_pivot.py
- tests/unit/domain/market/test_swing.py

## Modified files
- src/elliottwaver/domain/market/__init__.py

## Exclusions
- No infrastructure, application, or interface changes were made.

## Domain invariants
- Pivots require UTC timestamps and a `PivotType`.
- Swings require two distinct pivots with alternating pivot types,
  strictly increasing timestamps, identical symbol and timeframe, and a
  strictly directional price movement (LOW->HIGH increases, HIGH->LOW decreases).

## Acceptance criteria
- Types implemented: `PivotType`, `Pivot`, `SwingDirection`, `Swing`.
- All required invariants enforced at construction.
- Derived properties implemented: direction, symbol, timeframe, timestamps,
  duration, price_change, absolute_price_change.
- Unit tests added and passing locally.

## Validation results
- Validation to be performed: ruff format/check, mypy, pytest.

## Review status
- Implementation in progress; validation pending

## Commit status
- No commit created by the Copilot agent.

## Completion checklist
- [ ] Validation commands executed and results recorded
- [ ] Architectural review completed

## Implementation notes
- Added immutable domain objects for PivotType, Pivot, SwingDirection, and Swing.
- Enforced construction-time invariants for alternating pivot types, timestamps, symbols, timeframes, and directional price movement.
- Derived read-only properties expose direction, symbol, timeframe, timestamps, duration, and signed/absolute price change.
