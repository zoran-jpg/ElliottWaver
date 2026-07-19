# PROJECT_MANIFEST

## 1. Project Identity

- Project: ElliottWaver
- Type: Adaptive Market Decision Intelligence Platform
- Repository: C:\Users\User\Desktop\ElliottWaver
- Primary language: Python 3.12
- Build backend: Hatchling
- Package layout: src layout

## 2. Vision

Create a maintainable, testable, and architecture-driven platform for analyzing market behavior through Elliott Wave concepts while keeping the domain layer independent from external systems.

## 3. Mission

Provide a clean and extensible foundation for market analysis models, rules, scoring, and user-facing interfaces while preserving strong domain boundaries and high engineering quality.

## 4. Product Goal

Deliver a layered platform in which domain rules are explicit, validations are enforced, and quality gates remain reliable as the project evolves.

## 5. Scope

- Domain models and invariants for market data concepts
- Application orchestration and use cases
- Infrastructure adapters and persistence hooks
- Interface adapters for user interaction
- Documentation and engineering-process infrastructure

## 6. Non-Goals

- Implementing EP-002 Part 2 during this package
- Introducing infrastructure dependencies into the domain layer
- Replacing existing architecture decisions with ad hoc shortcuts
- Creating GitHub issues or pull requests in this package

## 7. Architecture

The architecture follows clean architecture and domain-driven design:

- interfaces -> application -> domain
- infrastructure -> application and domain abstractions
- bootstrap -> composition of required modules
- core -> technical shared primitives independent of Elliott Wave business logic

The current confirmed domain types are Price and Candle. The next planned domain types are Pivot and Swing.

## 8. Dependency Rules

- Domain code must not depend on application, infrastructure, interfaces, or bootstrap modules.
- Infrastructure may depend on domain abstractions and application ports.
- Application may orchestrate domain and infrastructure services.
- Interfaces may depend on application services and present data to users.

## 9. Project Layers

### Layer 1 – ChatGPT
- architecture
- roadmap
- Engineering Packages
- technical direction
- reviews
- root-cause analysis
- preservation of the project's architectural thread

### Layer 2 – GitHub Copilot Agent
- repository inspection
- implementation
- tests
- formatting
- validation
- structured implementation reports
- no commits or pushes

### Layer 3 – GitHub
- repository history
- Actions
- Issues
- pull requests
- releases
- traceability

### Layer 4 – Project Intelligence
- PROJECT_MANIFEST.md
- current status
- roadmap
- metrics
- decisions
- Engineering Package records
- central source of truth

## 10. Team Responsibilities

- ChatGPT: define architecture, roadmap, Engineering Packages, and technical direction.
- GitHub Copilot Agent: inspect, implement, test, validate, and report.
- GitHub: maintain repository history and workflow automation.
- User: review, approve, and decide when to proceed to the next package.

## 11. Development Workflow

1. Inspect repository state, relevant documentation, and source files.
2. Review the current Engineering Package requirements.
3. Implement only the assigned scope.
4. Add or update tests as needed.
5. Run formatting, linting, type checking, and tests.
6. Report results and await review before moving on.

## 12. Engineering Package Lifecycle

1. Define the package goal, scope, and acceptance criteria.
2. Inspect relevant files and current state.
3. Implement the package.
4. Validate with the required commands.
5. Review the results.
6. Mark the package as complete only after validation and review.

## 13. Coding Standards

- Follow Python 3.12 conventions.
- Use type hints consistently.
- Prefer explicit and readable code.
- Keep functions and classes focused.
- Preserve the existing package organization under src/elliottwaver.

## 14. Domain Standards

- Preserve Domain-Driven Design boundaries.
- Use immutable domain objects where appropriate.
- Use Decimal for financial values.
- Use timezone-aware UTC datetimes.
- Enforce invariants during construction.
- Avoid unnecessary abstractions.

## 15. Testing Standards

- Use pytest.
- Mirror source package paths in tests.
- Cover valid behavior, invalid states, and boundaries.
- Do not weaken or delete tests to make code pass.
- Keep tests deterministic and isolated.

## 16. Quality Gates

Run these commands before considering work complete:

- python -m ruff format .
- python -m ruff check .
- python -m mypy src tests
- python -m pytest
- git status

## 17. Git Rules

- Do not commit or push during package implementation unless explicitly requested.
- Review git status and diffs before editing.
- Preserve existing repository history.

## 18. GitHub Copilot Rules

- Inspect PROJECT_MANIFEST.md, CURRENT_STATUS.md, ROADMAP.md, the assigned Engineering Package file, and relevant source and test files before package work.
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

## 19. ChatGPT Architecture Rules

- Preserve the architectural thread across planning and implementation.
- Keep domain, application, infrastructure, and interfaces properly separated.
- Use root-cause analysis for issues and regressions.

## 20. Project Intelligence Rules

- Maintain PROJECT_MANIFEST.md as the authoritative constitution for the project.
- Keep project documentation synchronized with the current package state.
- Record decisions and metrics only when they are confirmed.
- Distinguish confirmed facts from estimates and future plans.

## 21. Roadmap Summary

- EP-001 – Foundation: Completed
- EP-001A – Project Intelligence: In Progress during this task
- EP-002 – Domain Core
  - Part 1: Price and Candle – Completed
  - Part 2: Pivot and Swing – Next
  - remaining parts: Planned
- EP-003 – Wave Engine: Planned
- EP-004 – Rule Engine: Planned
- EP-005 – Scoring Engine: Planned
- EP-006 – Application Layer: Planned
- EP-007 – Infrastructure: Planned
- EP-008 – Interfaces: Planned

## 22. Current Project Status

- Current branch: main
- Current package: EP-001A – Project Intelligence System
- Next planned domain package: EP-002 Part 2 – Pivot and Swing Domain Models
- Last confirmed validation: passed

## 23. Confirmed Metrics

- Python: 3.12.10
- Tests: 36 passed
- Coverage: 99.02%
- Ruff format: passed
- Ruff check: passed
- MyPy: passed
- MyPy scope: 40 source files
- Pytest: passed

## 24. Important Decisions

- Python 3.12 is the baseline runtime.
- The project uses src layout and Hatchling.
- Clean Architecture and Domain-Driven Design remain the governing design approach.
- Financial values use Decimal and time uses timezone-aware UTC datetimes.
- Engineering Packages are the delivery unit.

## 25. Current Risks

- Documentation can drift if package status updates are not maintained.
- The next domain package depends on careful preservation of existing architecture boundaries.

## 26. Next Planned Step

Complete EP-001A documentation and Project Intelligence infrastructure, then prepare for EP-002 Part 2 review.

## 27. Document Maintenance Rules

- Update documentation when a package is completed, reviewed, or materially changed.
- Preserve useful existing content and improve it where necessary.
- Mark estimates and future plans clearly.
- Do not present unverified metrics as confirmed facts.
