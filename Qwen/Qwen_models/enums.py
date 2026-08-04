"""Enumerations shared across all MAIS contracts.

String-valued enums keep JSON payloads human-readable while preserving strong
typing in Python. Values intentionally mirror the frozen Phase 1 platform and
language catalogs.
"""

from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    """Supported publishing platforms (mirrors config.json)."""

    YOUTUBE_SHORTS = "YouTube Shorts"
    INSTAGRAM_REELS = "Instagram Reels"
    JOSH = "Josh"
    PINTEREST = "Pinterest"
    MOJ = "Moj"


class Language(StrEnum):
    """Supported production languages."""

    ENGLISH = "English"
    HINDI = "Hindi"
    HINGLISH = "Hinglish"
    SPANISH = "Spanish"


class AgentType(StrEnum):
    """Production agents. Includes forward-looking agents for future expansion."""

    SCENE = "scene"
    VOICE = "voice"
    METADATA = "metadata"
    THUMBNAIL = "thumbnail"
    IMAGE = "image"
    VIDEO = "video"
    MERGE = "merge"
    QC = "qc"
    PUBLISHER = "publisher"
    # Reserved for future expansion (no implementation implied).
    SUBTITLE = "subtitle"
    MUSIC = "music"
    TRANSLATION = "translation"
    ANALYTICS = "analytics"
    SOCIAL_MEDIA = "social_media"
    BRAND_COMPLIANCE = "brand_compliance"


class TaskStatus(StrEnum):
    """Lifecycle status of a single agent task."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ExecutionStatus(StrEnum):
    """Lifecycle status of a run / job / manifest."""

    CREATED = "created"
    PLANNING = "planning"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class ArtifactType(StrEnum):
    """Logical media type of a produced artifact."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"
    SCRIPT = "script"
    DOCUMENT = "document"
    METADATA = "metadata"
    MANIFEST = "manifest"


class ArtifactState(StrEnum):
    """Persistence/verification state of an artifact."""

    PENDING = "pending"
    WRITING = "writing"
    COMMITTED = "committed"
    VERIFIED = "verified"
    CORRUPT = "corrupt"
    DELETED = "deleted"


class ErrorCategory(StrEnum):
    """Coarse classification used to drive retry policy decisions."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    VALIDATION = "validation"
    PROVIDER = "provider"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    DEPENDENCY = "dependency"
    QUOTA = "quota"
    UNKNOWN = "unknown"


class LogLevel(StrEnum):
    """Structured log severity."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ProviderKind(StrEnum):
    """Capability class of a provider. Config-driven, provider-agnostic."""

    LLM = "llm"
    TTS = "tts"
    IMAGE_GENERATION = "image_generation"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_GENERATION = "video_generation"
    LIP_SYNC = "lip_sync"
    TRANSCRIPTION = "transcription"
    MUSIC_GENERATION = "music_generation"
    STORAGE = "storage"
    PUBLISHING = "publishing"


class BackoffStrategy(StrEnum):
    """Delay growth strategy for retries."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class Environment(StrEnum):
    """Deployment environment."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AspectRatio(StrEnum):
    """Common canvas aspect ratios."""

    PORTRAIT_9_16 = "9:16"
    PORTRAIT_2_3 = "2:3"
    SQUARE_1_1 = "1:1"
    LANDSCAPE_16_9 = "16:9"