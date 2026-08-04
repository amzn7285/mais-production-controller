"""
Domain models.

Pydantic models are used (rather than plain dataclasses) for every
structure that crosses a boundary — Controller to Agent, Agent to
Provider, Controller to StateStore — because those boundaries are
exactly where the Creative Director's Master Production JSON and any
future API layer need validation and (de)serialization for free.

Plain `@dataclass` is used only for `RetryDecision`, a value object
that never crosses a serialization boundary and is constructed and
consumed entirely in-process.

No field in this module defaults to a concrete provider name, model
name, or platform-specific value — those live in configuration
supplied at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mais.production_controller.domain.enums import (
    AgentType,
    JobStatus,
    ProductionStage,
    ProviderCapability,
    PublishMode,
    StageStatus,
)


class MAISBaseModel(BaseModel):
    """Shared Pydantic base for the domain layer.

    `frozen=True` makes domain models immutable value objects —
    a stage produces a *new* model rather than mutating a shared one,
    which keeps concurrent/parallel agent execution safe by
    construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class ErrorDetail(MAISBaseModel):
    """Structured error information attached to a failed
    `AgentResponse`, distinct from raising an exception — lets the
    Controller inspect *why* a stage failed without unwinding the
    call stack."""

    code: str
    message: str
    retriable: bool
    provider_name: str | None = None


class MasterProductionReference(MAISBaseModel):
    """A pointer to the Creative Director's Master Production JSON,
    not a copy of it.

    The Production Controller consumes this JSON but must never
    modify it (per the frozen Phase 1 contract), so agents are handed
    a reference plus the specific fields they need rather than the
    full frozen document, keeping the boundary between "Creative
    Director output" and "Production Controller input" explicit.
    """

    job_id: str
    source_document_id: str
    retrieved_at: datetime


class ProviderDescriptor(MAISBaseModel):
    """Declares a provider's identity and capability without
    specifying implementation details.

    Config supplies an ordered list of these per stage; providers
    are never hardcoded into agent or controller code.
    """

    name: str
    capability: ProviderCapability
    priority: int = Field(ge=0, description="Lower value is tried first.")
    enabled: bool = True


class RetryPolicyConfig(MAISBaseModel):
    """Configuration for an `IRetryPolicy` implementation."""

    max_attempts: int = Field(ge=1)
    initial_backoff_seconds: float = Field(ge=0)
    backoff_multiplier: float = Field(ge=1)


class StageConfig(MAISBaseModel):
    """Per-stage configuration: which providers may serve this
    stage, in what order, with what retry policy and timeout."""

    stage: ProductionStage
    providers: tuple[ProviderDescriptor, ...]
    retry_policy: RetryPolicyConfig
    timeout_seconds: float = Field(gt=0)


class AgentRequest(MAISBaseModel):
    """The Controller's request to a single `IProductionAgent`."""

    job_id: str
    stage: ProductionStage
    agent_type: AgentType
    input_payload: dict[str, Any]
    stage_config: StageConfig


class AgentResponse(MAISBaseModel):
    """The standard response every `IProductionAgent` must return,
    matching the "Return Standard Response" lifecycle step defined
    for all production agents."""

    job_id: str
    stage: ProductionStage
    status: StageStatus
    output_payload: dict[str, Any] | None = None
    error: ErrorDetail | None = None
    provider_used: str | None = None
    started_at: datetime
    completed_at: datetime


class StageState(MAISBaseModel):
    """Persisted state for one stage of one job, as stored by an
    `IStateStore`. This is what makes a job resumable."""

    stage: ProductionStage
    status: StageStatus
    attempt_count: int = 0
    last_response: AgentResponse | None = None


class JobContext(MAISBaseModel):
    """The full persisted state of a production job: identity,
    overall status, and per-stage state. Passed to the Controller to
    resume a job, and returned by the Controller after each
    transition."""

    job_id: str
    master_production_ref: MasterProductionReference
    status: JobStatus
    stages: tuple[StageState, ...]
    created_at: datetime
    updated_at: datetime


class ExecutionPlan(MAISBaseModel):
    """The Controller's plan for a job: an ordered list of stage
    groups, where stages within a group may execute in parallel and
    groups execute sequentially.

    Modeling this explicitly (rather than a single flat list) is
    what lets the Controller run e.g. Voice, Metadata, and Image
    concurrently while still gating Merge behind all of them.
    """

    job_id: str
    stage_groups: tuple[tuple[ProductionStage, ...], ...]


class PlatformPublishingCapability(MAISBaseModel):
    """Declares whether a platform can be published to
    programmatically, per the Publishing Capability Matrix from the
    architecture review. Consumed by the Publisher Agent to decide
    whether to invoke a provider or hand off to a human."""

    platform: str
    publish_mode: PublishMode


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """In-process value object returned by an `IRetryPolicy`.

    Not a Pydantic model: this never leaves the process, is never
    serialized, and is created/consumed many times in a tight retry
    loop, where a plain dataclass is the leaner choice.
    """

    should_retry: bool
    wait_seconds: float
