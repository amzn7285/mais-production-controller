"""
Production Controller settings.

`ProductionControllerSettings` is the top-level, environment-loadable
configuration schema. It intentionally holds only cross-cutting
defaults and backend selection — per-stage provider lists
(`StageConfig`, `ProviderDescriptor` from `domain.models`) are
expected to be loaded separately (e.g. from a `stages.json`) and are
not embedded here, keeping "which providers exist" decoupled from
"how the controller behaves by default."
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from mais.production_controller.domain.constants import (
    DEFAULT_AGENT_TIMEOUT_SECONDS,
    DEFAULT_MAX_RETRY_ATTEMPTS,
    DEFAULT_PROVIDER_TIMEOUT_SECONDS,
    DEFAULT_RETRY_BACKOFF_MULTIPLIER,
    DEFAULT_RETRY_BACKOFF_SECONDS,
)


class ProductionControllerSettings(BaseSettings):
    """Environment-driven settings for the Production Controller.

    Values are read from environment variables prefixed
    `MAIS_PC_` (e.g. `MAIS_PC_STATE_STORE_BACKEND=sqlite`), or from
    a `.env` file, via `pydantic-settings`.
    """

    model_config = SettingsConfigDict(
        env_prefix="MAIS_PC_",
        env_file=".env",
        extra="forbid",
    )

    environment: str = Field(
        default="development",
        description="Deployment environment name, e.g. development, staging, production.",
    )

    state_store_backend: str = Field(
        default="sqlite",
        description=(
            "Identifier for which IStateStore implementation the "
            "composition root should wire in. Not a class path — "
            "resolved through the DI container, keeping this file "
            "free of import-time coupling to infrastructure."
        ),
    )

    event_publisher_backend: str = Field(
        default="log",
        description="Identifier for which IEventPublisher implementation to wire in.",
    )

    default_max_retry_attempts: int = Field(default=DEFAULT_MAX_RETRY_ATTEMPTS, ge=1)
    default_retry_backoff_seconds: float = Field(default=DEFAULT_RETRY_BACKOFF_SECONDS, ge=0)
    default_retry_backoff_multiplier: float = Field(
        default=DEFAULT_RETRY_BACKOFF_MULTIPLIER, ge=1
    )

    default_agent_timeout_seconds: float = Field(default=DEFAULT_AGENT_TIMEOUT_SECONDS, gt=0)
    default_provider_timeout_seconds: float = Field(
        default=DEFAULT_PROVIDER_TIMEOUT_SECONDS, gt=0
    )

    stage_config_path: str = Field(
        default="config/stages.json",
        description="Path to the per-stage provider/config document, loaded separately.",
    )

    max_parallel_agents: int = Field(
        default=4,
        ge=1,
        description="Upper bound on agents the Controller may run concurrently within a stage group.",
    )
