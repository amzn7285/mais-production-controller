"""
State Store interface.

Abstracts where `JobContext` / `StageState` are persisted (SQLite for
a zero-budget single-machine deployment, a hosted database later,
etc.). The Controller depends only on this interface, so the backing
store can change without touching orchestration code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mais.production_controller.domain.enums import ProductionStage
from mais.production_controller.domain.models import JobContext, StageState


class IStateStore(ABC):
    """Abstract contract for persisting and retrieving job state."""

    @abstractmethod
    async def save_job(self, job_context: JobContext) -> None:
        """Persist the full current state of `job_context`,
        overwriting any previously stored state for the same
        `job_id`."""
        raise NotImplementedError

    @abstractmethod
    async def load_job(self, job_id: str) -> JobContext:
        """Load the persisted `JobContext` for `job_id`.

        Raises `mais.production_controller.domain.exceptions
        .JobNotFoundError` if no state exists for `job_id`.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_stage_state(self, job_id: str, stage_state: StageState) -> None:
        """Persist an updated `StageState` for one stage of an
        existing job, without requiring the full `JobContext` to be
        re-saved. This is the primitive that makes checkpointing
        after each stage cheap.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_stage_state(self, job_id: str, stage: ProductionStage) -> StageState:
        """Load the persisted `StageState` for a single stage of an
        existing job."""
        raise NotImplementedError
