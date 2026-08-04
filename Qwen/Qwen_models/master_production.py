"""Master Production contract (Phase 1 output, frozen single source of truth).

The Creative Director produces this object. The Production Engine treats it as
read-only. Downstream components must not mutate or regenerate its content.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from . import constants as C
from .base import MaisImmutableModel
from .enums import Language, Platform
from .types import (
    ProductionId,
    ScriptText,
    SemanticVersion,
    ShortText,
    TopicText,
    UtcDatetime,
)


class ValidationCheck(MaisImmutableModel):
    """A single validation check result from the Creative Director."""

    name: ShortText
    passed: bool
    message: str | None = Field(default=None, max_length=2_000)


class ValidationResults(MaisImmutableModel):
    """Aggregated validation outcome attached to a MasterProduction."""

    is_valid: bool
    validated_at: UtcDatetime
    checks: tuple[ValidationCheck, ...] = Field(default_factory=tuple)
    errors: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _consistent(self) -> "ValidationResults":
        if self.is_valid and self.errors:
            raise ValueError("is_valid cannot be True while errors are present")
        return self


class ProductionConfiguration(MaisImmutableModel):
    """Platform-derived production parameters resolved by the Creative Director."""

    output_format: ShortText
    aspect_ratio: ShortText
    max_duration_seconds: int = Field(ge=1, le=C.MAX_DURATION_SECONDS)
    hook_style: ShortText
    call_to_action: ShortText
    hashtags: tuple[str, ...] = Field(default_factory=tuple, max_length=C.MAX_HASHTAGS)
    thumbnail_guidance: ShortText
    content_focus: ShortText
    language_style: ShortText


class ProductionMetadata(MaisImmutableModel):
    """Provenance metadata for a MasterProduction."""

    created_at: UtcDatetime
    created_by: ShortText
    source_system: str = C.SOURCE_SYSTEM_CREATIVE_DIRECTOR
    creative_director_version: SemanticVersion
    trace_id: str | None = Field(default=None, max_length=200)
    attributes: dict[str, Any] = Field(default_factory=dict)


class MasterProduction(MaisImmutableModel):
    """Immutable, validated production brief. Single source of truth.

    This is the only object downstream agents consume for creative decisions.
    It is frozen; any attempt to mutate it raises a validation error.
    """

    schema_version: SemanticVersion = C.MASTER_PRODUCTION_SCHEMA_VERSION
    production_id: ProductionId
    character: ShortText
    topic: TopicText
    platform: Platform
    language: Language
    audience: ShortText
    tone: ShortText
    script: ScriptText
    clean_script: ScriptText
    production_configuration: ProductionConfiguration
    validation_results: ValidationResults
    production_metadata: ProductionMetadata

    @model_validator(mode="after")
    def _require_valid(self) -> "MasterProduction":
        if not self.validation_results.is_valid:
            raise ValueError(
                "MasterProduction must carry passing validation_results before "
                "it can enter the Production Engine"
            )
        return self