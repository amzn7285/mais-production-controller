"""
Domain-level constants.

These are defaults only — every value here is expected to be
overridable via `config.settings` or per-job/per-stage configuration.
They exist so concrete implementations have a documented fallback
instead of inventing their own magic numbers independently.
"""

from __future__ import annotations

from typing import Final

# Retry defaults. Concrete `IRetryPolicy` implementations may ignore
# these entirely; they are fallbacks for configuration-driven callers
# that don't specify their own policy.
DEFAULT_MAX_RETRY_ATTEMPTS: Final[int] = 3
DEFAULT_RETRY_BACKOFF_SECONDS: Final[float] = 5.0
DEFAULT_RETRY_BACKOFF_MULTIPLIER: Final[float] = 2.0

# Timeout defaults, in seconds, for a single agent execution.
DEFAULT_AGENT_TIMEOUT_SECONDS: Final[float] = 60.0
DEFAULT_PROVIDER_TIMEOUT_SECONDS: Final[float] = 30.0

# Job/state identifiers.
JOB_ID_PREFIX: Final[str] = "MAIS"

# Config keys shared across layers, defined once to avoid drift
# between the Controller, agents, and settings loader.
CONFIG_KEY_PROVIDERS: Final[str] = "providers"
CONFIG_KEY_FALLBACK_ORDER: Final[str] = "fallback_order"
CONFIG_KEY_RETRY_POLICY: Final[str] = "retry_policy"
CONFIG_KEY_TIMEOUT_SECONDS: Final[str] = "timeout_seconds"
