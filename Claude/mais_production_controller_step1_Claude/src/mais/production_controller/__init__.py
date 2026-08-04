"""
MAIS Production Controller.

Phase 2 of Media AI Studio. Consumes the frozen Creative Director
Master Production JSON and orchestrates production agents
(Voice, Scene, Metadata, Thumbnail, Image, Video, Merge, QC,
Publisher) without performing AI generation itself.

This package currently exposes structure only:

- `domain`         Framework-independent entities, enums, exceptions,
                    constants. No dependency on anything outside this
                    package.
- `interfaces`      Abstract ports (Agent, Provider, Controller,
                    StateStore, RetryPolicy, EventPublisher) that
                    concrete implementations will satisfy in later
                    steps.
- `application`     Reserved for use-case / orchestration logic
                    (Step 2+). Intentionally empty in Step 1.
- `infrastructure`  Reserved for concrete adapters and the DI
                    container wiring (Step 2+). Intentionally empty
                    in Step 1 except for the DI container port.
- `config`          Configuration schema (Pydantic models) for the
                    controller. No provider names or values are
                    hardcoded here.
"""
