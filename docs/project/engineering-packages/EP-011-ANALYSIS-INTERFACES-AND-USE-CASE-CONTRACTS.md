# EP-011 – Analysis Interfaces & Use-Case Contracts

Status: In Progress

## Background

This package introduces a deterministic application boundary for analysis requests.
It exposes request/response contracts, use-case protocols, and orchestration services
without pushing infrastructure concerns into the domain layer.

## Goal

Provide a stable analysis application surface that can be consumed by inbound adapters
while preserving the domain pipeline and its deterministic ordering rules.

## Scope

Included:
- AnalysisStage
- AnalysisIssueSeverity
- TimeframeAnalysisRequest
- AnalysisRequest
- AnalysisIssue
- AnalysisMetadata
- TimeframeAnalysisResult
- AnalysisResponse
- MarketDataProvider
- AnalysisClock
- AnalysisIdProvider
- CandleToSwingPreparationPort
- AnalyzeTimeframeUseCase
- AnalyzeMultiTimeframeUseCase
- AnalyzeTimeframeService
- AnalyzeMultiTimeframeService
- Public re-exports from src/elliottwaver/application and src/elliottwaver/interfaces
- Unit tests for validation, immutability, protocol compatibility, and orchestration behavior

Excluded:
- Direct infrastructure adapters
- UI, CLI, API routing, or transport concerns
- Recomputing detection, scoring, selection, hierarchy, or confluence inside the application layer
- Trading execution logic

## Inspect list

- Repository state
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- docs/project/DECISIONS.md
- src/elliottwaver/application/analysis.py
- src/elliottwaver/application/__init__.py
- src/elliottwaver/interfaces/analysis.py
- src/elliottwaver/interfaces/__init__.py
- tests/unit/application/test_analysis.py

## Create list

- docs/project/engineering-packages/EP-011-ANALYSIS-INTERFACES-AND-USE-CASE-CONTRACTS.md

## Modify list

- src/elliottwaver/application/analysis.py
- src/elliottwaver/application/__init__.py
- src/elliottwaver/interfaces/analysis.py
- src/elliottwaver/interfaces/__init__.py
- tests/unit/application/test_analysis.py
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- docs/project/DECISIONS.md

## Functional requirements

- Validate analysis request and response metadata deterministically.
- Normalize timeframe requests with stable ordering.
- Expose use-case protocols for single-timeframe and multi-timeframe analysis.
- Orchestrate domain components through explicit ports only.
- Preserve immutability for request, issue, metadata, and response models.

## Architecture constraints

- Keep the application layer independent from infrastructure adapters.
- Preserve the domain pipeline boundaries established by earlier packages.
- Use explicit ports for time, IDs, market data, and candle-to-swing preparation.
- Do not recompute domain analysis inside the application service layer.

## Test requirements

- Add or update tests for request validation and orchestration behavior.
- Keep protocol compatibility tests focused on observable behavior.
- Avoid weakening the deterministic ordering and metadata checks.

## Validation commands

- python -m ruff format tests/unit/application/test_analysis.py
- python -m ruff check tests/unit/application/test_analysis.py
- python -m pytest --no-cov tests/unit/application/test_analysis.py

## Acceptance criteria

- Analysis application contracts are implemented.
- Interfaces re-export the analysis boundary.
- The test slice passes.
- Project Intelligence documents reflect the new package.
- Full repository validation remains pending until the broader gates are run.

## Risk assessment

- The full repo still needs global validation against Ruff, MyPy, and pytest coverage gates.
- Any future adapter work must preserve the explicit port boundaries introduced here.

## Time estimate

- Completed in this session with remaining full-repo validation pending.

## Final report format

- Summary
- Files created
- Files modified
- Validation results
- Follow-up items

## Documentation update requirements

- Keep the package record aligned with the current repository state.
- Do not mark the package complete before full validation and review.

## Explicit stop conditions

- Stop before changing architecture or roadmap without explicit approval.
- Stop if validation reveals unresolved issues.
- Do not commit or push.
- Do not automatically begin the next package.