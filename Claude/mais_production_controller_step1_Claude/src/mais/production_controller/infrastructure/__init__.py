"""
Infrastructure layer.

Reserved for concrete adapters that satisfy the `interfaces` ports —
specific provider clients, a specific `IStateStore` backend (e.g.
SQLite), a specific `IEventPublisher` sink. Depends on `domain` and
`interfaces`; nothing in `domain`, `interfaces`, or `application`
may import from `infrastructure`, which keeps provider and backend
choices swappable without touching orchestration logic.

Intentionally empty in Step 1 except for the dependency-injection
container port (`infrastructure.di`), which defines *how* concrete
adapters will be wired without wiring any yet.
"""
