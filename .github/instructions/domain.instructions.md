---
applyTo: "src/elliottwaver/domain/**/*.py"
---

# Domain design instructions

- Preserve Domain-Driven Design boundaries and keep the domain layer focused on business concepts.
- The domain layer must not depend on application, infrastructure, interfaces, or bootstrap modules.
- Prefer immutable domain objects where the concept is naturally value-based.
- Use Decimal for all financial values and monetary calculations.
- Use timezone-aware UTC datetimes for any time-based domain state.
- Enforce invariants during object construction and reject invalid states immediately.
- Avoid unnecessary abstractions; keep the model simple and explicit.
