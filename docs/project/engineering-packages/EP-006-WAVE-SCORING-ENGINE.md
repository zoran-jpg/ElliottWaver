# EP-006 – Wave Scoring Engine

Status: Architecture approved, implementation in progress

## Background

This package adds deterministic and extensible scoring for detected wave candidates.
The scoring step evaluates candidate quality without selecting a single final winner.

## Goal

Provide an objective, reproducible scoring engine for valid WaveCandidate inputs using
independent weighted criteria and deterministic sorting.

## Scope

Included:
- ScoreComponent model
- WaveScore model
- WaveScorer service
- ScoringResult model
- Sorting by score descending with deterministic tie-breaking
- Modular scoring criteria infrastructure
- Unit tests for scoring models, scorer behavior, determinism, sorting, ties, and immutability

Excluded:
- Best-candidate selection
- ML/probability/forecast logic
- Fibonacci calculations (only extensibility placeholder)
- Persistence, API, GUI, CLI, parallelism

## Created files
- src/elliottwaver/domain/scoring/wave_scorer.py
- src/elliottwaver/domain/scoring/__init__.py
- tests/unit/domain/scoring/test_wave_scorer.py

## Modified files
- docs/project/ROADMAP.md
- docs/project/status/CURRENT_STATUS.md
- docs/project/DECISIONS.md

## Scoring architecture
- Scoring is separate from detection and rules.
- WaveScorer consumes valid WaveCandidate instances and computes criterion components.
- WaveScore aggregates weighted components and yields total score plus percentage.
- ScoringResult stores scored candidates and applies deterministic sorting.
- Duplicate wave IDs are ignored during scoring.

## Criteria infrastructure
- wave_proportions
- swing_symmetry
- impulse_consistency
- rule_compliance_bonus
- fibonacci_extension_placeholder

Weights are centralized in ScoringConfig for straightforward extension.

## Acceptance criteria
- Models and scorer are implemented and immutable where applicable.
- Scores are deterministic and within 0-100%.
- Sorting is stable and deterministic on ties.
- Full quality gate commands are executed and recorded.

## Validation results
- python -m ruff format .: passed
- python -m ruff check .: passed
- python -m mypy src tests: passed (no issues in 55 source files)
- python -m pytest: passed (97 passed, coverage 92.91%)

## Review status
- In Review

## Commit status
- No commit created by the Copilot agent.
