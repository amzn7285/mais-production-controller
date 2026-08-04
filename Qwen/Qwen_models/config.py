"""Configuration contracts: retry policy, provider config, runtime config.

Configuration-only. No provider behavior or implementation lives here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import AnyUrl, Field, model_validator

from . import constants as C
from .base import MaisImmutableModel
from .enums import BackoffStrategy, Environment, LogLevel, ProviderKind
from .types import ProviderId, SemanticVersion


class RetryPolicy(MaisImmutableModel):
    """Declarative retry behavior applied to a task."""

    max_attempts: int = Field(default=C.DEFAULT_MAX_ATTEMPTS, ge=1, le=20)
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    initial_delay_seconds: float = Field(default=C.DEFAULT_INITIAL_DELAY_SECONDS, gt=0)
    max_delay_seconds: float = Field(default=C.DEFAULT_MAX_DELAY_SECONDS, gt=0)
    backoff_multiplier: float = Field(default=C.DEFAULT_BACKOFF_MULTIPLIER, ge=1.0)
    jitter: bool = True
    retryable_error_categories: tuple[str, ...] = Field(
        default_factory=lambda: tuple(C.DEFAULT_RETRYABLE_ERROR_CATEGORIES)
    )

    @model_validator(mode="after")
    def _validate_delays(self) -> "RetryPolicy":
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds must be >= initial_delay_seconds")
        return self


class ProviderConfig(MaisImmutableModel):
    """Provider registration metadata. Secrets are references only, never inline."""

    provider_id: ProviderId
    kind: ProviderKind
    display_name: str = Field(min_length=1, max_length=200)
    base_url: AnyUrl | None = None
    # Must be a reference (env:/secret:/vault:), never a raw credential.
    auth_secret_ref: str | None = Field(
        default=None,
        max_length=200,
        pattern=r"^(env|secret|vault):[\w.\-/]+$",
    )
    model_slug: str | None = Field(default=None, max_length=200)
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=1000)
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    timeout_seconds: int = Field(default=C.DEFAULT_TIMEOUT_SECONDS, ge=1)
    capabilities: tuple[str, ...] = Field(default_factory=tuple)
    extra: dict[str, Any] = Field(default_factory=dict)


class RuntimeConfig(MaisImmutableModel):
    """Aggregate runtime configuration for a production run."""

    schema_version: SemanticVersion = C.RUNTIME_CONFIG_SCHEMA_VERSION
    environment: Environment
    output_directory: Path
    default_timeout_seconds: int = Field(default=C.DEFAULT_TIMEOUT_SECONDS, ge=1)
    default_retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    max_parallelism: int = Field(default=C.DEFAULT_MAX_PARALLELISM, ge=1, le=1024)
    log_level: LogLevel = LogLevel.INFO
    providers: tuple[ProviderConfig, ...] = Field(default_factory=tuple)
    feature_flags: dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_providers(self) -> "RuntimeConfig":
        provider_ids = [p.provider_id for p in self.providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider_id values must be unique within RuntimeConfig")
        return self