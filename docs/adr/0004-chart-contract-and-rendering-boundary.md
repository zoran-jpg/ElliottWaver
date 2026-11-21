# ADR-0004: Chart Contract and Rendering Boundary

- Status: Accepted
- Date: 2026-11-21

## Context

Chart rendering needs deterministic, UI-independent input while preserving domain/application boundaries and avoiding duplicate market logic in the UI.

## Decision

Use an application-level immutable chart contract as the only data source for chart rendering:

- Mapping from analysis/forecast/projection output happens in the application layer.
- Tk chart code consumes only mapped contract payloads and performs no market recomputation.
- Wave labels (for example 1-5 or A-B-C) are rendered only when unambiguously derivable from selected-wave structure.

## Consequences

- UI cannot invent or reclassify market structure.
- Rendering behavior is deterministic and unit-testable.
- Look-ahead leakage risk is reduced by contract-level confirmation constraints.

## Alternatives considered

- UI-side wave/swing derivation: rejected to avoid duplicate logic and architecture drift.
