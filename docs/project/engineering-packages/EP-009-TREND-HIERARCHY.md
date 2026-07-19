# EP-009 – Trend Hierarchy & Parent/Child Wave Relations

Status: Implementation in progress

## Background

This package introduces a structural hierarchy layer that links selected waves
across timeframes without interpreting market direction. The hierarchy is built
from existing multi-timeframe analysis outputs.

## Goal

Provide immutable hierarchy models and a deterministic builder that connects
selected wave candidates by timeframe order only.

## Scope

Included:
- TrendNode
- ParentChildRelation
- RelationType
- TrendHierarchy
- TrendHierarchyBuilder
- HierarchyValidationResult
- Unit tests for node behavior, relations, hierarchy properties, validation,
  builder determinism, ordering, and selection-only orchestration

Excluded:
- Trend scoring/evaluation
- Bullish/bearish interpretation
- Forecasting and Fibonacci logic
- Confluence analysis
- Trading signals and entry/exit logic
- Machine learning
- Persistence, API, GUI, CLI, infrastructure, parallel processing

## Created files
- src/elliottwaver/domain/trend_hierarchy/trend_hierarchy.py
- src/elliottwaver/domain/trend_hierarchy/__init__.py
- tests/unit/domain/trend_hierarchy/test_trend_hierarchy.py

## Modified files
- docs/project/status/CURRENT_STATUS.md
- docs/project/ROADMAP.md
- docs/project/DECISIONS.md

## Trend hierarchy architecture
- TrendNode binds one selected wave candidate to exactly one timeframe level.
- ParentChildRelation models only structural links between timeframe levels.
- TrendHierarchy stores nodes and relations with derived properties for root,
  leaves, depth, node count, and validity.
- TrendHierarchyBuilder consumes MultiTimeframeAnalysis and builds hierarchy
  deterministically based on timeframe order only.
- HierarchyValidationResult validates structural consistency without raising
  exceptions for business-invalid hierarchy states.

## Acceptance criteria
- Immutable hierarchy models are implemented.
- Builder is deterministic and side-effect free.
- Structural validation covers roots, cycles, duplicates, and consistency.
- Existing pipeline components remain unchanged.
- Full quality gates are executed and recorded.

## Validation results
- python -m ruff format .: passed
- python -m ruff check .: passed
- python -m mypy src tests: passed (no issues in 64 source files)
- python -m pytest: passed (123 passed, coverage 91.46%)

## Review status
- In Review

## Commit status
- No commit created by the Copilot agent.
