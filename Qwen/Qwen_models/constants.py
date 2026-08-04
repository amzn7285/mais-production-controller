"""Shared constants for MAIS contracts.

Pure data. No behavior. Values here are the single source of truth for
defaults and limits referenced by the models.
"""

from __future__ import annotations

# --- Contract / schema versioning -------------------------------------------
MAIS_CONTRACTS_VERSION = "1.0.0"
MASTER_PRODUCTION_SCHEMA_VERSION = "1.0.0"
EXECUTION_PLAN_SCHEMA_VERSION = "1.0.0"
AGENT_RESULT_SCHEMA_VERSION = "1.0.0"
PRODUCTION_MANIFEST_SCHEMA_VERSION = "1.0.0"
RUNTIME_CONFIG_SCHEMA_VERSION = "1.0.0"

API_VERSION = "v1"

# --- Provenance -------------------------------------------------------------
SOURCE_SYSTEM_CREATIVE_DIRECTOR = "creative_director"
DEFAULT_LOGGER_NAME = "mais"

# --- Retry defaults ---------------------------------------------------------
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_INITIAL_DELAY_SECONDS = 1.0
DEFAULT_MAX_DELAY_SECONDS = 60.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_RETRYABLE_ERROR_CATEGORIES: tuple[str, ...] = (
    "transient",
    "rate_limit",
    "timeout",
)

# --- Execution defaults -----------------------------------------------------
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_PARALLELISM = 4

# --- Content limits ---------------------------------------------------------
MAX_HASHTAGS = 30
MAX_SCRIPT_LENGTH = 50_000
MAX_TOPIC_LENGTH = 1_000
MAX_DURATION_SECONDS = 3_600

# --- Media / integrity ------------------------------------------------------
DEFAULT_CONTENT_TYPE_JSON = "application/json"
CHECKSUM_ALGORITHM_SHA256 = "sha256"