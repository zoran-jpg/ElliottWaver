# EP-005 – Wave Detection Engine

Status: Implementation in progress

## Background

This package adds deterministic wave-candidate detection on top of existing
Swing, Wave, and Rule foundations. Detection remains separate from rule
definitions and does not include scoring, ranking, or best-candidate selection.

## Goal

Build a deterministic WaveDetector that derives connected swing-chain windows,
constructs Wave candidates, and validates each candidate through WaveRuleSet.

## Scope

Included:
- WaveCandidate model
- DetectionResult model
- WaveDetector component
- Deterministic candidate generation from ordered Swing sequences
- RuleSet-based candidate validation
- Unit tests for empty input, valid/invalid outcomes, multiple candidates,
  order determinism, deduplication, and immutability

Excluded:
- Scoring or ranking
- Best-candidate selection
- Confidence scores
- Fibonacci or forecasting logic
- Infrastructure, persistence, APIs, CLI, GUI, async/parallel processing

## Created files
- src/elliottwaver/domain/detection/wave_detector.py
- src/elliottwaver/domain/detection/__init__.py
- tests/unit/domain/detection/test_wave_detector.py

## Modified files
- docs/project/ROADMAP.md
- docs/project/status/CURRENT_STATUS.md
- docs/project/DECISIONS.md

## Candidate strategy
- Input swings are treated as ordered and are never reordered.
- Swings are split into contiguous connected chains.
- For each chain, all contiguous windows with at least two swings are evaluated.
- A deterministic Wave id is derived from the Swing id sequence.
- Constructively invalid windows are skipped (DomainError stays a construction guard).
- Rule-valid and rule-invalid candidates are both retained in DetectionResult.
- Duplicate candidate windows are removed by swing-id sequence keys.

## Architecture notes
- Detection logic is isolated in domain/detection and not embedded in Wave, Swing,
  or rule classes.
- WaveDetector uses WaveRuleSet but does not define rules.
- Business-invalid candidates are represented through RuleViolation entries,
  not by raising DomainError in detection flow.

## Acceptance criteria
- WaveCandidate, DetectionResult, and WaveDetector are implemented.
- Multiple candidates and mixed valid/invalid results are supported.
- Empty input returns empty result without errors.
- Detection remains deterministic and duplicate-free.
- Quality gates are executed and recorded.

## Validation results
- python -m ruff format .: passed
- python -m ruff check .: passed
- python -m mypy src tests: passed (no issues in 52 source files)
- python -m pytest: passed (82 passed, coverage 91.68%)

## Review status
- In Review

## Commit status
- No commit created by the Copilot agent.
