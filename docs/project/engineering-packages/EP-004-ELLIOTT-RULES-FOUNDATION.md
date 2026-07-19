# EP-004 – Elliott Rules Foundation

Status: Implementation in progress

## Background

This engineering package introduces the first reusable rule-validation foundation for
Elliott wave constraints. It stays fully inside the domain layer and does not include
wave detection, scoring, infrastructure adapters, or interface concerns.

## Goal

Create an extensible rule architecture and implement the first three impulse-wave
rules for Wave 2, Wave 3, and Wave 4 constraints.

## Scope

Included:
- Domain rule contracts and result models
- Rule aggregation via a rule set
- Three impulse-wave rules:
  - Wave2RetracementRule
  - Wave3NotShortestRule
  - Wave4NoOverlapRule
- Unit tests for valid/invalid scenarios and aggregation behavior

Excluded:
- Wave detection
- Scoring/ranking
- Fibonacci calculations
- Diagonal exceptions
- Alternation and extension logic beyond the listed rules
- Application/infrastructure/interface/persistence changes

## Created files
- src/elliottwaver/domain/rules/wave_rules.py
- src/elliottwaver/domain/rules/__init__.py
- tests/unit/domain/rules/test_wave_rules.py

## Modified files
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- docs/project/DECISIONS.md

## Architecture decisions in this package
- Rules evaluate to RuleResult and RuleViolation objects instead of raising DomainError
  for business-invalid wave outcomes.
- Rule evaluation is deterministic and stateless.
- WaveRuleSet aggregates violations from multiple independent rules.
- Each rule is responsible for one business condition.

## Acceptance criteria
- Rule foundation types exist in domain:
  - WaveRule
  - RuleViolation
  - RuleResult
  - WaveRuleSet
- The three required rules are implemented.
- Violations are aggregated without throwing DomainError for invalid outcomes.
- Unit tests cover valid and invalid behavior and aggregation scenarios.
- Full validation commands are executed and recorded.

## Validation results
- python -m ruff format .: passed
- python -m ruff check .: passed
- python -m mypy src tests: passed (no issues in 49 source files)
- python -m pytest: passed (69 passed, coverage 90.93%)

## Review status
- In Review

## Commit status
- No commit created by the Copilot agent.
