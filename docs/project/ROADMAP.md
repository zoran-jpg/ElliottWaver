# Project roadmap

The roadmap below reflects the currently established Engineering Package plan. Percentages are planning indicators only and are not measured product-completion percentages.

## EP-001 – Foundation
- Purpose: establish the repository structure, package layout, and core configuration.
- Status: Completed
- Dependencies: none
- Expected outputs: repository skeleton, packaging, and initial documentation
- Known next step: none
- Progress indicator: 100%

## EP-001A – Project Intelligence System
- Purpose: create the central Project Intelligence layer for manifest, status, roadmap, metrics, decisions, and package records.
- Status: In Progress during this task
- Dependencies: EP-001
- Expected outputs: PROJECT_MANIFEST.md, project intelligence documentation, and updated Copilot guidance
- Known next step: complete and review the documentation package
- Progress indicator: 70% (planning indicator only)

## EP-002 – Domain Core
### Part 1: Price and Candle
- Purpose: define the initial domain value objects for prices and candles.
- Status: Completed
- Dependencies: EP-001
- Expected outputs: Price and Candle domain models and tests
- Known next step: none
- Progress indicator: 100%

### Part 2: Pivot and Swing
- Purpose: define the next domain models for pivot and swing concepts.
- Status: Next
- Dependencies: EP-002 Part 1
- Expected outputs: Pivot and Swing domain models and tests
- Known next step: implement after EP-001A review
- Progress indicator: 20% (planning indicator only)

### Remaining parts
- Status: Planned
- Dependencies: EP-002 Part 2 and earlier work
- Expected outputs: additional domain package increments as needed
- Known next step: confirm scope after the current domain package
- Progress indicator: 10% (planning indicator only)

## EP-003 – Wave Engine
- Purpose: implement the wave analysis engine.
- Status: Planned
- Dependencies: EP-002
- Expected outputs: wave engine components and tests
- Known next step: define the package scope once domain core is stable
- Progress indicator: 10% (planning indicator only)

## EP-004 – Rule Engine
- Purpose: implement market rules and decision heuristics.
- Status: Planned
- Dependencies: EP-003
- Expected outputs: rule engine modules and tests
- Known next step: confirm rule interfaces after the wave engine
- Progress indicator: 10% (planning indicator only)

## EP-005 – Scoring Engine
- Purpose: implement scoring and ranking logic.
- Status: Planned
- Dependencies: EP-004
- Expected outputs: scoring engine modules and tests
- Known next step: define scoring inputs and outputs
- Progress indicator: 10% (planning indicator only)

## EP-006 – Application Layer
- Purpose: implement application use cases and orchestration.
- Status: Planned
- Dependencies: EP-005
- Expected outputs: application services and tests
- Known next step: define use cases after scoring rules stabilize
- Progress indicator: 10% (planning indicator only)

## EP-007 – Infrastructure
- Purpose: implement infrastructure adapters and persistence hooks.
- Status: Planned
- Dependencies: EP-006
- Expected outputs: adapters and integration seams
- Known next step: define external interfaces and storage boundaries
- Progress indicator: 10% (planning indicator only)

## EP-008 – Interfaces
- Purpose: implement user-facing adapters such as CLI, API, or GUI layers.
- Status: Planned
- Dependencies: EP-007
- Expected outputs: interface adapters and tests
- Known next step: define the user experience entry points
- Progress indicator: 10% (planning indicator only)
