# ADR-0005: Dependency, CI, and Packaging Strategy

- Status: Accepted
- Date: 2026-11-21

## Context

Release confidence requires reproducible installs, package integrity checks, and cross-platform quality gates.

## Decision

Adopt a constraints-driven Python packaging and CI strategy:

- Runtime and development constraints are maintained in `constraints/runtime.txt` and `constraints/dev.txt`.
- Installation commands use interpreter-bound `python -m pip`.
- CI quality workflow targets Linux and Windows with the same quality gates.
- Wheel smoke checks run against installed artifacts in fresh virtual environments, including `pip check` and CLI/module smoke.

## Consequences

- Local and CI environments share pinned dependency intent.
- Packaging regressions are detected against built wheels, not only source trees.
- Final cross-platform release confidence still depends on executed CI runs.

## Alternatives considered

- Unconstrained editable installs only: rejected due to weaker reproducibility guarantees.
