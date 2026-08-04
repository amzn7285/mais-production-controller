"""
Application layer.

Reserved for use-case / orchestration implementations — e.g. the
concrete `IProductionController` implementation, execution-plan
builders, and stage-execution coordinators. Depends on `domain` and
`interfaces` only, never on `infrastructure` directly (concrete
adapters are injected at composition time, see
`infrastructure/di`).

Intentionally empty in Step 1: this package exists to fix the layer
boundary now, before any orchestration logic is written, so that
logic has an unambiguous home from the start.
"""
