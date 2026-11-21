# ADR-0002: Desktop Controller and View Separation

- Status: Accepted
- Date: 2026-11-21

## Context

The desktop adapter must remain responsive and testable while preserving clean-architecture boundaries. Tk widgets are hard to test in isolation and should not orchestrate analysis workflow directly.

## Decision

Use an explicit controller/view split in the desktop interface:

- View owns widgets and user interaction wiring.
- Controller owns orchestration state and delegates analysis execution.
- Presentation payloads are immutable and passed from controller to view.

## Consequences

- UI behavior can be validated with deterministic controller tests.
- Tk code remains focused on rendering and event dispatch.
- Analysis orchestration stays independent from concrete widget internals.

## Alternatives considered

- Keep all logic in a single Tk class: rejected because it mixes rendering and orchestration and harms testability.
