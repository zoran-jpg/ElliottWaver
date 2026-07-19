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
- Status: Completed
- Dependencies: EP-002 Part 1
- Expected outputs: Pivot and Swing domain models and tests
- Known next step: none
- Progress indicator: 100% (planning indicator only)

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
- Status: In Progress
- Dependencies: EP-003
- Expected outputs: rule engine modules and tests
- Known next step: validate the Elliott Rules Foundation package and collect review feedback
- Progress indicator: 35% (planning indicator only)

## EP-005 – Wave Detection Engine
- Purpose: deterministically derive wave candidates from ordered swing sequences and validate them with the rule foundation.
- Status: In Progress
- Dependencies: EP-004
- Expected outputs: detection components, candidate/result models, and tests
- Known next step: complete review of EP-005 detection behavior and candidate strategy
- Progress indicator: 35% (planning indicator only)

## EP-006 – Wave Scoring Engine
- Purpose: score valid wave candidates objectively and reproducibly without selecting a single winner.
- Status: In Progress
- Dependencies: EP-005
- Expected outputs: scoring components, weighted criteria, and deterministic ranking output
- Known next step: review scoring behavior and confirm weighting strategy for next package
- Progress indicator: 35% (planning indicator only)

## EP-007 – Wave Selection Engine
- Purpose: deterministically select pre-scored wave candidates using pluggable policies.
- Status: In Progress
- Dependencies: EP-006
- Expected outputs: selection policies, selector service, and immutable selection result models
- Known next step: review selection policy behavior and progression criteria
- Progress indicator: 35% (planning indicator only)

## EP-008 – Multi-Timeframe Analysis Foundation
- Purpose: orchestrate existing selection results across multiple timeframes with deterministic ordering.
- Status: In Progress
- Dependencies: EP-007
- Expected outputs: timeframe value object, analysis models, and orchestration service
- Known next step: review multi-timeframe invariants and progression criteria
- Progress indicator: 35% (planning indicator only)

## EP-009 – Trend Hierarchy & Parent/Child Wave Relations
- Purpose: model deterministic structural parent/child relationships between selected waves across timeframes.
- Status: Completed
- Dependencies: EP-008
- Expected outputs: hierarchy models, validation result model, and deterministic builder
- Known next step: review hierarchy invariants and package progression criteria
- Progress indicator: 35% (planning indicator only)

## EP-010 – Multi-Timeframe Confluence Engine
- Purpose: evaluate deterministic confluence signals over an existing trend hierarchy without recomputing upstream analysis.
- Status: In Review
- Dependencies: EP-009
- Expected outputs: confluence rules, evidence/conflict models, analyzer, and tests
- Known next step: review confluence package results and confirm progression criteria
- Progress indicator: 90% (planning indicator only)

## EP-011 – Analysis Interfaces & Use-Case Contracts
- Purpose: define deterministic analysis application contracts and inbound interface facades above the domain pipeline.
- Status: In Progress
- Dependencies: EP-010
- Expected outputs: analysis request/response contracts, orchestration services, interface facades, and tests
- Known next step: complete validation and review of the analysis application boundary
- Progress indicator: 75% (planning indicator only)
