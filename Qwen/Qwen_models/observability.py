"""Observability contracts: structured logs and job status snapshots."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from .base import MaisImmutableModel
from .enums import AgentType, ExecutionStatus, LogLevel
from .types import JobId, ProgressPercent, RunId, StageId, TaskId, UtcDatetime, utc_now


class LogEntry(MaisImmutableModel):
    """A single structured log record."""

    timestamp: UtcDatetime = Field(default_factory=utc_now)
    level: LogLevel
    message: str = Field(min_length=1, max_length=10_000)
    run_id: RunId | None = None
    task_id: TaskId | None = None
    agent_type: AgentType | None = None
    logger_name: str = Field(default="mais", max_length=200)
    context: dict[str, Any] = Field(default_factory=dict)


class TaskCounts(MaisImmutableModel):
    """Task status tallies for a job."""

    total: int = Field(default=0, ge=0)
    pending: int = Field(default=0, ge=0)
    running: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _sum_matches(self) -> "TaskCounts":
        parts = self.pending + self.running + self.completed + self.failed + self.skipped
        if parts != self.total:
            raise ValueError("task counts must sum to total")
        return self


class JobStatus(MaisImmutableModel):
    """Point-in-time status snapshot of a production job."""

    job_id: JobId
    run_id: RunId
    status: ExecutionStatus
    progress_percent: ProgressPercent = 0.0
    current_stage_id: StageId | None = None
    summary: str | None = Field(default=None, max_length=1_000)
    task_counts: TaskCounts = Field(default_factory=TaskCounts)
    updated_at: UtcDatetime = Field(default_factory=utc_now)