# Project decisions

This index records accepted project decisions that are currently in effect.

## Decision index

| ID | Title | Status | Context | Decision | Consequences | ADR |
| --- | --- | --- | --- | --- | --- | --- |
| DEC-001 | Python 3.12 | Accepted | The project needs a modern, stable runtime for development and validation. | Use Python 3.12 as the supported runtime. | Tooling and code style are aligned with Python 3.12. | ADR not yet created |
| DEC-002 | src layout | Accepted | The repository needs a package structure that is installable and explicit. | Use the src layout with packages under src/elliottwaver. | Imports are stable and packaging is straightforward. | ADR not yet created |
| DEC-003 | Hatchling build backend | Accepted | The project needs a pip-compatible build backend. | Use Hatchling as the build backend. | The package can be built and installed with standard tooling. | ADR not yet created |
| DEC-004 | pip-compatible dev dependencies | Accepted | Development tooling must be installable through the existing dependency configuration. | Define a dev optional dependency group in pyproject.toml. | Local validation tooling can be installed consistently. | ADR not yet created |
| DEC-005 | Clean Architecture and DDD | Accepted | The project needs strong separation between business logic and infrastructure. | Use Clean Architecture and Domain-Driven Design. | The domain remains testable and independent from external systems. | [docs/adr/0001-clean-architecture.md](docs/adr/0001-clean-architecture.md) |
| DEC-006 | Decimal for financial values | Accepted | Financial calculations require precision. | Use Decimal for financial values. | Monetary calculations avoid floating-point rounding issues. | ADR not yet created |
| DEC-007 | Timezone-aware UTC datetimes | Accepted | Domain values should be unambiguous and comparable. | Use timezone-aware UTC datetimes for time-based domain state. | Temporal data is consistent and explicit. | ADR not yet created |
| DEC-008 | Strict MyPy | Accepted | The project needs strong static guarantees for maintainability. | Run mypy in strict mode for src and tests. | Type issues are caught earlier in development. | ADR not yet created |
| DEC-009 | Ruff for formatting and linting | Accepted | The project needs consistent formatting and lint rules. | Use Ruff for formatting and linting. | Style and correctness issues are enforced consistently. | ADR not yet created |
| DEC-010 | pytest and pytest-cov | Accepted | The project needs reliable automated tests and coverage reporting. | Use pytest and pytest-cov. | Tests and coverage are integrated into the workflow. | ADR not yet created |
| DEC-011 | 90% minimum coverage | Accepted | The project needs a minimum quality bar for test coverage. | Enforce 90% minimum coverage in pytest configuration. | Regression risk is reduced and coverage remains visible. | ADR not yet created |
| DEC-012 | Engineering Packages as delivery unit | Accepted | The project needs a clear unit for planning and implementation. | Use Engineering Packages as the delivery unit. | Work is scoped, reviewed, and tracked consistently. | ADR not yet created |
| DEC-013 | No Copilot commits or pushes | Accepted | The repository should remain under deliberate human review for commits and pushes. | Copilot must not create commits or pushes during package work. | Repository history remains intentional and reviewable. | ADR not yet created |
| DEC-014 | Mandatory architectural review before commit | Accepted | Architectural integrity must be protected as the project grows. | Review architecture and dependency boundaries before committing. | Cross-layer violations are reduced. | ADR not yet created |
| DEC-015 | Four-layer development model | Accepted | The project needs clear roles across planning and implementation. | Use ChatGPT, GitHub Copilot Agent, GitHub, and Project Intelligence as the four layers. | Responsibilities are clear and coordinated. | ADR not yet created |
| DEC-016 | PROJECT_MANIFEST.md as primary source of truth | Accepted | The project needs a single authoritative constitution for long-term planning and guidance. | Use PROJECT_MANIFEST.md as the primary source of truth. | Documentation remains consistent and centralized. | ADR not yet created |
