# Copilot instructions for ElliottWaver

## Project context
- This repository implements an adaptive market decision intelligence platform.
- Keep the domain layer independent from brokers, databases, APIs, UI, and AI providers.
- Prefer a clean architecture structure with domain logic under src/elliottwaver/domain and supporting infrastructure under src/elliottwaver/infrastructure.

## Project Intelligence rules
- PROJECT_MANIFEST.md is the primary project source of truth.
- CURRENT_STATUS.md is the source of truth for the current operational state.
- ROADMAP.md is the source of truth for planned packages.
- METRICS.md contains confirmed and historical quality measurements.
- DECISIONS.md contains accepted project decisions.
- Conflicts must be reported, not silently resolved.
- Copilot may update project-status documents only when explicitly requested.
- Copilot must not mark an Engineering Package completed before validation and user review.
- Copilot must not write unverified metrics.
- Copilot must not change architecture or roadmap implicitly.

## Required inspection before every Engineering Package
- PROJECT_MANIFEST.md
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- the assigned Engineering Package file
- relevant source and test files

## Coding standards
- Follow Python 3.12 conventions and keep code compatible with the versions declared in pyproject.toml.
- Use type hints consistently and prefer explicit, readable code over clever shortcuts.
- Favor small, focused functions and classes with clear responsibilities.
- Preserve the existing package organization under src/elliottwaver.

## Style and tooling
- Follow Ruff formatting and linting rules defined in pyproject.toml.
- Keep imports sorted and avoid unused code.
- Prefer Pydantic models and value objects where they fit the domain model.
- Use pytest for unit tests and place them under tests/unit.

## Testing expectations
- When changing behavior, add or update unit tests in the corresponding tests/unit module.
- Keep tests focused on observable behavior and avoid over-mocking.
- Maintain or improve test coverage; the project target is 90% coverage.

## Validation
Before considering work complete, verify with:
- python -m ruff format .
- python -m ruff check .
- python -m mypy src tests
- python -m pytest
- git status
