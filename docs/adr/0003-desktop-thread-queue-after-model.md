# ADR-0003: Desktop Thread Queue after Model

- Status: Accepted
- Date: 2026-11-21

## Context

Running analysis synchronously blocks the Tk main loop. Direct worker-thread widget access is unsafe.

## Decision

Adopt a background-worker model with explicit main-thread handoff:

- Analysis runs in one worker thread per active request.
- Results are transferred via a thread-safe queue.
- UI updates happen only on the Tk main thread via `after(...)` polling.

## Consequences

- Desktop remains responsive during analysis.
- Main-thread-only Tk safety is enforced by design.
- Error handling and lifecycle transitions are deterministic and testable.

## Alternatives considered

- Synchronous UI-thread analysis: rejected due to UI blocking.
- Direct worker-to-widget updates: rejected due to Tk thread-safety risk.
