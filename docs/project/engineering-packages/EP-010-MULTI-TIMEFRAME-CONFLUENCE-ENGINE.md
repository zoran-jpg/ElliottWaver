# EP-010 – Multi-Timeframe Confluence Engine

Status: In Review

## Background

This package adds a deterministic confluence layer above the existing trend hierarchy.
It interprets parent/child structural relations using immutable domain models and
rule-based evidence/conflict reporting without recomputing upstream detection,
scoring, or selection results.

## Goal

Provide a domain-only confluence engine that evaluates structural alignment across
hierarchy relations and produces stable, explainable confluence results.

## Scope

Included:
- ConfluenceSeverity
- ConfluenceConfig
- ConfluenceEvidence
- ConfluenceConflict
- ConfluenceRuleResult
- ConfluenceRule protocol
- DirectionAlignmentRule
- TemporalContainmentRule
- StructuralContinuityRule
- ScoreSupportRule
- RelationConfluenceResult
- MultiTimeframeConfluenceResult
- MultiTimeframeConfluenceAnalyzer
- Unit tests for validation, rule behavior, aggregation, determinism, and no recomputation

Excluded:
- Trend interpretation outside the hierarchy layer
- Recomputing detection, scoring, or selection results
- Application, infrastructure, or interface adapters
- Trading signals or execution logic

## Created files
- src/elliottwaver/domain/confluence/confluence_engine.py
- src/elliottwaver/domain/confluence/__init__.py
- tests/unit/domain/confluence/test_confluence_engine.py

## Modified files
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- docs/project/DECISIONS.md

## Confluence architecture
- ConfluenceConfig centralizes deterministic thresholds and evidence weights.
- ConfluenceEvidence and ConfluenceConflict capture positive and negative observations.
- ConfluenceRuleResult aggregates per-rule outcomes without side effects.
- Rule implementations interpret existing node, wave, and score data only.
- RelationConfluenceResult aggregates a single parent/child relation.
- MultiTimeframeConfluenceResult aggregates all relations in a hierarchy.
- MultiTimeframeConfluenceAnalyzer evaluates relations without recomputing upstream analysis.

## Acceptance criteria
- Immutable confluence models are implemented.
- Rule evaluation is deterministic and explainable.
- Invalid states raise DomainError at construction time.
- Analyzer reuses hierarchy and score inputs without recomputation.
- Unit tests cover valid behavior, invalid states, aggregation, and determinism.
- Full quality gates are executed and recorded.

## Validation results
- python -m ruff format .: passed
- python -m ruff check .: passed
- python -m mypy src tests: passed (no issues in 67 source files)
- python -m pytest: passed (153 passed, coverage 91.64%)

## Review status
- In Review

## Commit status
- No commit created by the Copilot agent.
