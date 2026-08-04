"""Execution planning and runtime state contracts.

Specification objects (plan, stage, task, context) are immutable. ExecutionState
is mutable because it tracks live progress. No orchestration logic is included.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from . import constants as C
from .base import MaisBaseModel, MaisImmutableModel
from .config import RetryPolicy, RuntimeConfig
from .enums import AgentType, Environment, ExecutionStatus
from .types import (
    ArtifactId,
    PlanId,
    ProductionId,
    RunId,
    StageId,
    TaskId,
    UtcDatetime,
    utc_now,
)


class AgentTask(MaisImmutableModel):
    """Immutable specification of a single unit of agent work."""

    task_id: TaskId
    agent_type: AgentType
    stage_id: StageId | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    input_artifact_refs: tuple[ArtifactId, ...] = Field(default_factory=tuple)
    depends_on_tasks: tuple[TaskId, ...] = Field(default_factory=tuple)
    retry_policy: RetryPolicy | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)
    priority: int = Field(default=0, ge=0, le=1000)
    idempotency_key: str = Field(min_length=8, max_length=256)
    provider_preference: tuple[str, ...] = Field(default_factory=tuple)


class ExecutionStage(MaisImmutableModel):
    """An ordered wave of tasks that may run in parallel."""

    stage_id: StageId
    name: str = Field(min_length=1, max_length=200)
    order: int = Field(ge=0)
    tasks: tuple[AgentTask, ...]
    depends_on_stages: tuple[StageId, ...] = Field(default_factory=tuple)
    description: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def _non_empty(self) -> "ExecutionStage":
        if not self.tasks:
            raise ValueError("an execution stage must contain at least one task")
        return self


class ExecutionPlan(MaisImmutableModel):
    """Immutable, fully-resolved production plan derived from a MasterProduction."""

    plan_id: PlanId
    run_id: RunId
    production_id: ProductionId
    plan_version: int = Field(default=1, ge=1)
    created_at: UtcDatetime
    stages: tuple[ExecutionStage, ...]
    max_parallelism: int = Field(default=C.DEFAULT_MAX_PARALLELISM, ge=1)
    default_timeout_seconds: int = Field(default=C.DEFAULT_TIMEOUT_SECONDS, ge=1)
    default_retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    notes: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def _validate_plan(self) -> "ExecutionPlan":
        if not self.stages:
            raise ValueError("execution plan must define at least one stage")

        orders = [stage.order for stage in self.stages]
        if len(orders) != len(set(orders)):
            raise ValueError("stage order values must be unique")

        task_ids = [task.task_id for stage in self.stages for task in stage.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("task_id values must be unique across the plan")
        return self


class ExecutionState(MaisBaseModel):
    """Mutable runtime progress for a run. Updated by the controller only."""

    run_id: RunId
    plan_id: PlanId
    status: ExecutionStatus = ExecutionStatus.CREATED
    current_stage_id: StageId | None = None
    pending_task_ids: list[TaskId] = Field(default_factory=list)
    running_task_ids: list[TaskId] = Field(default_factory=list)
    completed_task_ids: list[TaskId] = Field(default_factory=list)
    failed_task_ids: list[TaskId] = Field(default_factory=list)
    skipped_task_ids: list[TaskId] = Field(default_factory=list)
    attempts_by_task: dict[TaskId, int] = Field(default_factory=dict)
    started_at: UtcDatetime | None = None
    updated_at: UtcDatetime = Field(default_factory=utc_now)


class ExecutionContext(MaisImmutableModel):
    """Immutable per-run context propagated to all agents."""

    run_id: RunId
    plan_id: PlanId
    production_id: ProductionId
    correlation_id: str = Field(min_length=1, max_length=128)
    environment: Environment
    actor: str = Field(min_length=1, max_length=200)
    created_at: UtcDatetime = Field(default_factory=utc_now)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=256)
    trace_id: str | None = Field(default=None, max_length=128)
    runtime_config: RuntimeConfig