"""
Production Controller interface.

The Controller orchestrates agents; per the frozen architectural
principle from `PRODUCTION_ENGINE.md`, it never performs AI
generation itself. This interface exposes exactly the
responsibilities assigned to the Controller: build an execution
plan, run it, and support retrying a single failed stage — nothing
else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mais.production_controller.domain.enums import ProductionStage
from mais.production_controller.domain.models import (
    ExecutionPlan,
    JobContext,
    MasterProductionReference,
)


class IProductionController(ABC):
    """Abstract contract for the Production Controller."""

    @abstractmethod
    async def build_execution_plan(
        self, master_production_ref: MasterProductionReference
    ) -> ExecutionPlan:
        """Derive an `ExecutionPlan` (ordered, parallelizable stage
        groups) for the given Master Production reference.

        Raises `mais.production_controller.domain.exceptions
        .StageDependencyError` if a valid plan cannot be built.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute(self, plan: ExecutionPlan) -> JobContext:
        """Execute every stage group in `plan`, in order, running
        stages within a group concurrently, and return the resulting
        `JobContext`.

        Individual stage failures are reflected in the returned
        `JobContext.stages`, not raised — the Controller only raises
        for failures in orchestration itself (e.g. state store
        unavailable), matching the separation between "a stage
        failed" and "the Controller failed."
        """
        raise NotImplementedError

    @abstractmethod
    async def retry_stage(self, job_id: str, stage: ProductionStage) -> JobContext:
        """Re-run a single previously failed stage for an existing
        job and return the updated `JobContext`.

        Enables resuming a job from a checkpoint instead of
        re-running the full plan from the beginning.
        """
        raise NotImplementedError
