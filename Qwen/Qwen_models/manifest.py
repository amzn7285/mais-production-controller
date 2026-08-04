"""Production manifest: the aggregated, mutable record of a run's outputs."""

from __future__ import annotations

from pydantic import Field

from .base import MaisBaseModel
from .enums import ExecutionStatus
from .results import AgentResult, Artifact
from .types import ManifestId, PlanId, ProductionId, RunId, UtcDatetime, utc_now


class ProductionManifest(MaisBaseModel):
    """Mutable manifest assembled by the controller over the life of a run.

    Collects artifacts and results and summarizes cost/duration. It is mutated
    incrementally, then typically frozen/archived at run completion.
    """

    manifest_id: ManifestId
    run_id: RunId
    production_id: ProductionId
    plan_id: PlanId
    created_at: UtcDatetime = Field(default_factory=utc_now)
    updated_at: UtcDatetime = Field(default_factory=utc_now)
    status: ExecutionStatus = ExecutionStatus.CREATED
    artifacts: list[Artifact] = Field(default_factory=list)
    results: list[AgentResult] = Field(default_factory=list)
    total_duration_ms: int = Field(default=0, ge=0)
    cost_units: float = Field(default=0.0, ge=0.0)
    notes: str | None = Field(default=None, max_length=2_000)