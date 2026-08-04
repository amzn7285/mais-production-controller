# MAIS Production Controller — Step 1: Structure & Interfaces

This package delivers **only** the enterprise project structure and
foundational interfaces for the MAIS Production Controller. It
contains **no business logic** — every method body is either an
`abstractmethod` or, in the case of `AgentFactory`-style aliases, a
type declaration. Concrete orchestration, agents, and provider
adapters are out of scope for this step.

## Folder Tree

```
mais/
├── pyproject.toml
├── .env.example
├── README.md
├── src/
│   └── mais/
│       ├── __init__.py
│       └── production_controller/
│           ├── __init__.py
│           ├── domain/
│           │   ├── __init__.py
│           │   ├── enums.py
│           │   ├── constants.py
│           │   ├── exceptions.py
│           │   └── models.py
│           ├── interfaces/
│           │   ├── __init__.py
│           │   ├── agent.py
│           │   ├── provider.py
│           │   ├── controller.py
│           │   ├── state_store.py
│           │   ├── retry_policy.py
│           │   └── event_publisher.py
│           ├── application/
│           │   └── __init__.py
│           ├── infrastructure/
│           │   ├── __init__.py
│           │   └── di/
│           │       ├── __init__.py
│           │       └── container.py
│           └── config/
│               ├── __init__.py
│               └── settings.py
└── tests/
    ├── __init__.py
    └── production_controller/
        └── __init__.py
```

## Layering Rule (Clean Architecture)

Dependencies point inward only:

```
infrastructure  →  application  →  interfaces  →  domain
```

`domain` imports nothing from this package. `interfaces` imports only
`domain`. `application` (reserved for Step 2) will import `domain`
and `interfaces`. `infrastructure` (mostly reserved for Step 2+)
imports `domain` and `interfaces` and provides concrete
implementations of the abstract contracts — nothing upstream ever
imports from `infrastructure` directly; it's wired in through
`infrastructure.di`.

This is what makes the system provider-agnostic and DI-ready: the
Controller and every agent depend on `IProvider`, `IStateStore`,
`IRetryPolicy`, and `IEventPublisher` — never on a concrete class —
so any conforming implementation can be substituted at composition
time without touching orchestration code.

## File-by-File Purpose

### `src/mais/__init__.py`
Top-level namespace package for MAIS. Exists so `production_controller`
sits inside a proper `mais.*` namespace shared with future MAIS
subsystems (e.g. a future `mais.creative_director` package) rather
than being a standalone top-level import.

### `src/mais/production_controller/__init__.py`
Documents the package's public surface and layer responsibilities in
one place, so a new contributor (or a future you) can read one
docstring and understand the whole layout before opening any other
file.

### `domain/__init__.py`
Marks and documents the domain layer's boundary rule: it must never
import from `interfaces`, `application`, or `infrastructure`.

### `domain/enums.py`
`ProductionStage`, `AgentType`, `JobStatus`, `StageStatus`,
`PublishMode`, `ProviderCapability`. A single, typed vocabulary
shared by config, agents, and the Controller — the reason no stage,
agent kind, or publishing mode is ever a raw string literal anywhere
else in the codebase.

### `domain/constants.py`
Default retry counts, backoff values, and timeouts, plus shared
config-dictionary key names. Centralized so no two files invent
their own magic number or key name independently; every value here
is explicitly documented as an overridable default, not a hardcoded
rule.

### `domain/exceptions.py`
The full exception hierarchy (`MAISProductionError` and its
subclasses: `ConfigurationError`, `ValidationError`,
`ProviderUnavailableError`, `AllProvidersExhaustedError`,
`AgentExecutionError`, `StageDependencyError`, `StateStoreError`,
`JobNotFoundError`, `PublishingNotSupportedError`). Gives every
future implementation a consistent, catchable set of failure types
instead of raising bare `Exception` or ad hoc classes per module.

### `domain/models.py`
Pydantic models for everything that crosses a layer boundary
(`AgentRequest`, `AgentResponse`, `JobContext`, `StageState`,
`ExecutionPlan`, `ProviderDescriptor`, `StageConfig`,
`RetryPolicyConfig`, `PlatformPublishingCapability`,
`MasterProductionReference`, `ErrorDetail`) plus one plain
`@dataclass` (`RetryDecision`) for an in-process-only value object.
Models are `frozen=True` so a stage produces a new object rather than
mutating shared state — required for safe parallel execution of
independent agents.

### `interfaces/__init__.py`
States the port/adapter rule for this layer: abstract contracts
only, concrete implementations always live in `infrastructure` or
`application` and depend on these interfaces, never the reverse.

### `interfaces/agent.py`
`IProductionAgent` — the contract every concrete agent (Scene, Voice,
Metadata, Thumbnail, Image, Video, Lip Sync, Merge, QC, Publisher)
must satisfy. Exists so the Controller can depend on "an agent for
stage X" without knowing which concrete class implements it.

### `interfaces/provider.py`
`IProvider` and `IProviderResolver`. `IProvider` wraps a single
external/local capability; `IProviderResolver` implements the
fallback-order selection pattern (try provider A, then B, then C)
in exactly one place, shared by every agent, instead of duplicated
per agent.

### `interfaces/controller.py`
`IProductionController` — build a plan, execute a plan, retry a
single stage. Matches exactly the three responsibilities assigned to
the Controller in the architecture review; deliberately excludes
anything resembling AI generation, preserving the frozen "controller
never generates" principle.

### `interfaces/state_store.py`
`IStateStore` — save/load a job, update/get a single stage's state.
The `update_stage_state` / `get_stage_state` split (rather than only
whole-job save/load) is what makes cheap per-stage checkpointing
possible.

### `interfaces/retry_policy.py`
`IRetryPolicy` — `configure` + `decide`. Makes retry behavior
(fixed vs. exponential backoff, jitter, etc.) swappable per stage via
`RetryPolicyConfig` without changing Controller code.

### `interfaces/event_publisher.py`
`IEventPublisher` — a single `publish(event_name, payload)` method.
Decouples "a stage completed/failed/retried" from "what happens with
that fact" (logging today, an audit trail or notification later).

### `application/__init__.py`
Reserved, empty package for Step 2's concrete `IProductionController`
implementation and execution-plan/stage-coordination logic. Created
now so the layer boundary is fixed before any orchestration code
exists, rather than retrofitted later.

### `infrastructure/__init__.py`
Reserved package for concrete adapters (a specific `IStateStore`
backend, specific provider clients). Documents that nothing outside
`infrastructure` may import it directly — adapters are resolved
through `infrastructure.di` instead.

### `infrastructure/di/__init__.py`
Documents that this subpackage holds the DI container port, not yet
any concrete wiring.

### `infrastructure/di/container.py`
`IServiceContainer` — `register_singleton`, `register_factory`,
`resolve`, generic over `TService`. Defines the shape any DI
container (a specific library, or a hand-rolled composition root)
must satisfy, so the choice of DI mechanism is itself swappable and
is never imported directly by `domain`, `interfaces`, or
`application`.

### `config/__init__.py`
Documents that this package holds configuration *schema* only — no
provider names, model names, or platform values are hardcoded here.

### `config/settings.py`
`ProductionControllerSettings` (Pydantic `BaseSettings`,
env-prefixed `MAIS_PC_`) — cross-cutting defaults (retry, timeout,
max parallel agents) and *backend identifiers* (e.g.
`state_store_backend: "sqlite"`) rather than concrete import paths,
so `infrastructure.di` wiring — not this file — decides which class
an identifier maps to.

### `tests/__init__.py`, `tests/production_controller/__init__.py`
Test package roots, structured to mirror the source tree so tests
for a given source module are always easy to locate. Empty in Step
1 since interfaces have no runtime behavior to exercise yet.

### `pyproject.toml`
Declares the `src/`-layout package, Python ≥3.11 requirement, and
the only two runtime dependencies this step needs: `pydantic` and
`pydantic-settings`. No provider SDKs are declared — those are added
only when a concrete adapter using them is implemented, keeping this
step's dependency footprint minimal and provider-agnostic.

### `.env.example`
Documents every `ProductionControllerSettings` field and its default
as an environment variable, so configuring a deployment never
requires reading `settings.py` itself.

## Package Dependencies

Runtime:
- `pydantic>=2.6,<3.0` — domain models, validation at every layer boundary
- `pydantic-settings>=2.2,<3.0` — environment-driven `ProductionControllerSettings`

Development:
- `pytest>=8.0`, `pytest-asyncio>=0.23` — async-aware test runner, ready for Step 2
- `mypy>=1.9` — strict type checking (`strict = true` in `pyproject.toml`)
- `ruff>=0.4` — linting

## What This Step Deliberately Does Not Include

- Any concrete agent implementation
- Any concrete provider client
- Any concrete `IStateStore`, `IRetryPolicy`, `IEventPublisher`, or
  `IServiceContainer` implementation
- Any wiring/composition root
- Any FastAPI/CLI entrypoint

Those are Step 2+, and this structure is built specifically so none
of them require changes to `domain` or `interfaces` when added.
