"""
Shared enumerations for the Production Controller domain.

Centralizing these as enums (rather than free-form strings scattered
across agents and config) is what makes the pipeline configuration-
driven and provider-agnostic: every layer refers to the same finite,
typed vocabulary instead of re-declaring string literals.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class ProductionStage(str, Enum):
    """A discrete stage in the production pipeline.

    Ordering and parallelism between stages is a concern of the
    Controller's execution plan, not of this enum — this enum only
    names the stages that can exist.
    """

    SCENE_GENERATION = "scene_generation"
    VOICE_GENERATION = "voice_generation"
    METADATA_GENERATION = "metadata_generation"
    THUMBNAIL_GENERATION = "thumbnail_generation"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    LIP_SYNC = "lip_sync"
    MERGE = "merge"
    QUALITY_CONTROL = "quality_control"
    PUBLISH = "publish"


@unique
class AgentType(str, Enum):
    """The class of production agent, independent of any concrete
    implementation or provider it may eventually use."""

    SCENE = "scene"
    VOICE = "voice"
    METADATA = "metadata"
    THUMBNAIL = "thumbnail"
    IMAGE = "image"
    VIDEO = "video"
    LIP_SYNC = "lip_sync"
    MERGE = "merge"
    QUALITY_CONTROL = "quality_control"
    PUBLISHER = "publisher"


@unique
class JobStatus(str, Enum):
    """Lifecycle status of a production job as a whole."""

    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@unique
class StageStatus(str, Enum):
    """Lifecycle status of a single stage within a job."""

    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPLETED = "completed"


@unique
class PublishMode(str, Enum):
    """Whether a platform can be published to programmatically.

    Exists so the Publisher Agent's contract can express "this
    platform has no public API" as data (see the Publishing
    Capability Matrix from the architecture review) rather than as
    an implicit assumption or a special case in code.
    """

    API = "api"
    MANUAL = "manual"


@unique
class ProviderCapability(str, Enum):
    """The capability a provider offers, used to select candidate
    providers for a given stage without hardcoding provider names."""

    TEXT_GENERATION = "text_generation"
    TEXT_TO_SPEECH = "text_to_speech"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    LIP_SYNC = "lip_sync"
    MEDIA_MERGE = "media_merge"
    PUBLISHING = "publishing"
