"""Shared constrained types, identifier aliases, and small pure helpers.

This module defines reusable Annotated types and identifier/timestamp helpers.
It contains no business logic and no orchestration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from pydantic import AfterValidator, Field


# --- Timestamp helpers ------------------------------------------------------
def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime) -> datetime:
    """Coerce naive datetimes to UTC and normalize aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(_ensure_utc)]


# --- Identifier aliases -----------------------------------------------------
_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"

Identifier = Annotated[
    str,
    Field(min_length=3, max_length=128, pattern=_ID_PATTERN),
]

RunId = Identifier
TaskId = Identifier
StageId = Identifier
PlanId = Identifier
ArtifactId = Identifier
ResultId = Identifier
JobId = Identifier
ManifestId = Identifier
ProductionId = Identifier
ProviderId = Identifier


# --- Scalar constrained types ----------------------------------------------
SemanticVersion = Annotated[
    str,
    Field(pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$"),
]

MimeType = Annotated[
    str,
    Field(pattern=r"^[A-Za-z0-9_.+-]+/[A-Za-z0-9_.+-]+$"),
]

ProgressPercent = Annotated[float, Field(ge=0.0, le=100.0)]

ShortText = Annotated[str, Field(min_length=1, max_length=500)]
TopicText = Annotated[str, Field(min_length=1, max_length=1_000)]
ScriptText = Annotated[str, Field(min_length=1, max_length=50_000)]


# --- Identifier generators --------------------------------------------------
def _generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def generate_run_id() -> str:
    return _generate_id("run")


def generate_task_id() -> str:
    return _generate_id("task")


def generate_stage_id() -> str:
    return _generate_id("stage")


def generate_plan_id() -> str:
    return _generate_id("plan")


def generate_artifact_id() -> str:
    return _generate_id("art")


def generate_result_id() -> str:
    return _generate_id("res")


def generate_job_id() -> str:
    return _generate_id("job")


def generate_manifest_id() -> str:
    return _generate_id("mfst")


def generate_production_id() -> str:
    return _generate_id("prod")