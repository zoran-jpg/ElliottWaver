# Architecture overview

ElliottWaver follows Domain-Driven Design and Clean Architecture.

- `domain`: business concepts and invariants
- `application`: use cases and ports
- `infrastructure`: technical adapters
- `interfaces`: inbound adapters
- `bootstrap`: dependency composition
- `core/shared`: stable primitives

The domain must not import broker SDKs, database clients, web frameworks, UI frameworks, or ML frameworks.
