# EP-007 – Wave Selection Engine

Status: Implementation in progress

## Background

This package introduces deterministic candidate selection as an explicit step after
scoring. Selection remains independent from detection and scoring computation and
supports pluggable policies.

## Goal

Provide a standalone WaveSelector with interchangeable selection policies that
operate on pre-scored candidates without recalculating scores.

## Scope

Included:
- SelectionPolicy protocol
- SelectionConfig
- SelectionReason
- SelectedWaveCandidate
- SelectionResult
- WaveSelector
- Policies:
  - TopScoreSelectionPolicy
  - MinimumScoreSelectionPolicy
  - ScoreGapSelectionPolicy
- Unit tests for policies, models, selector delegation, determinism, tie behavior,
  deduplication, empty outcomes, and immutability

Excluded:
- Detection reruns
- Rule reruns
- Score recalculation
- Fibonacci computation
- Forecasting, probabilities, ML
- Infrastructure, API, CLI, GUI, persistence, parallelism

## Created files
- src/elliottwaver/domain/selection/wave_selector.py
- src/elliottwaver/domain/selection/__init__.py
- tests/unit/domain/selection/test_wave_selector.py

## Modified files
- docs/project/engineering-packages/EP-006-WAVE-SCORING-ENGINE.md
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- docs/project/DECISIONS.md

## Selection architecture
- Selection consumes existing ScoringResult and never recomputes scores.
- Policies are exchangeable and deterministic.
- SelectionResult is immutable and includes:
  - selected candidates
  - applied policy
  - considered-candidate count
  - has_selection/is_empty/selected_count/primary_candidate
- Empty selection is a valid business outcome.

## Policy behavior summary
- TopScoreSelectionPolicy: picks first scored candidate (stable order on ties).
- MinimumScoreSelectionPolicy: selects all candidates meeting threshold.
- ScoreGapSelectionPolicy: selects top candidate only when score gap is sufficient.

## Acceptance criteria
- Selection module is implemented with strict invariants and immutable outputs.
- Deterministic tie behavior uses existing ScoringResult order.
- Invalid config/rank/duplicate states are rejected early.
- Full quality gates are executed and recorded.

## Validation results
- python -m ruff format .: passed
- python -m ruff check .: passed
- python -m mypy src tests: passed (no issues in 58 source files)
- python -m pytest: passed (107 passed, coverage 92.25%)

## Review status
- In Review

## Commit status
- No commit created by the Copilot agent.
