"""Result, artifact, metrics, and error contracts produced by agents."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from .base import MaisImmutableModel
from .enums import AgentType, ArtifactState, ArtifactType, ErrorCategory, TaskStatus
from .types import ArtifactId, MimeType, ResultId, RunId, TaskId, UtcDatetime, utc_now


class Checksum(MaisImmutableModel):
    """Integrity digest for an artifact."""

    algorithm: str = Field(min_length=1, max_length=32)
    digest: str = Field(min_length=8, max_length=256, pattern=r"^[0-9a-fA-F]+$")


class Artifact(MaisImmutableModel):
    """A single produced asset reference with integrity metadata."""

    artifact_id: ArtifactId
    artifact_type: ArtifactType
    uri: str = Field(min_length=1, max_length=2_000)
    content_type: MimeType
    size_bytes: int = Field(ge=0)
    checksum: Checksum
    state: ArtifactState = ArtifactState.COMMITTED
    created_at: UtcDatetime = Field(default_factory=utc_now)
    produced_by_task: TaskId | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Metrics(MaisImmutableModel):
    """Execution metrics attached to a result."""

    duration_ms: int = Field(ge=0)
    attempt_count: int = Field(default=1, ge=1)
    tokens_input: int | None = Field(default=None, ge=0)
    tokens_output: int | None = Field(default=None, ge=0)
    cost_units: float = Field(default=0.0, ge=0.0)
    custom: dict[str, float] = Field(default_factory=dict)


class ErrorInfo(MaisImmutableModel):
    """Structured error detail for a failed task."""

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2_000)
    category: ErrorCategory
    is_retryable: bool = False
    provider_error_ref: str | None = Field(default=None, max_length=500)
    occurred_at: UtcDatetime = Field(default_factory=utc_now)


class AgentResult(MaisImmutableModel):
    """Immutable, standard response returned by an agent for one task."""

    result_id: ResultId
    task_id: TaskId
    run_id: RunId
    agent_type: AgentType
    status: TaskStatus
    provider_id: str | None = Field(default=None, max_length=200)
    model_slug: str | None = Field(default=None, max_length=200)
    attempts: int = Field(ge=1)
    started_at: UtcDatetime
    finished_at: UtcDatetime
    duration_ms: int = Field(ge=0)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    artifacts: tuple[Artifact, ...] = Field(default_factory=tuple)
    metrics: Metrics | None = None
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def _validate_result(self) -> "AgentResult":
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must be >= started_at")
        if self.status is TaskStatus.FAILED and self.error is None:
            raise ValueError("error must be provided when status is FAILED")
        return self