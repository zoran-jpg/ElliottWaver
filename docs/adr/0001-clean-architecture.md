# ADR-0001: Clean Architecture and DDD

- Status: Accepted
- Date: 2026-07-19

## Decision

Use Domain-Driven Design with inward-pointing dependencies and explicit application ports.

## Consequences

- Domain logic remains testable without infrastructure.
- External systems are replaceable adapters.
- Cross-layer shortcuts are rejected during review.
