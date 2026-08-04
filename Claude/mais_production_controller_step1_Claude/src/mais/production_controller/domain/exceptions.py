"""
Domain exception hierarchy.

Every exception raised anywhere in the Production Controller
subsystem inherits from `MAISProductionError`, so callers (API
layers, CLIs, the Controller itself) can catch at whatever
granularity they need — the whole subsystem, a category, or a
specific failure — without depending on any concrete agent or
provider implementation.
"""

from __future__ import annotations

from typing import Any


class MAISProductionError(Exception):
    """Base class for all Production Controller domain errors."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context or {}


class ConfigurationError(MAISProductionError):
    """Raised when required configuration is missing or invalid.

    Covers cases such as a stage with no configured providers, or a
    malformed retry policy — anything that should fail fast at
    startup or plan-build time rather than mid-execution.
    """


class ValidationError(MAISProductionError):
    """Raised when an agent's input or output fails validation
    against its declared contract."""


class ProviderUnavailableError(MAISProductionError):
    """Raised by an `IProvider` when it cannot currently service a
    request (e.g. rate limited, unauthenticated, unreachable).

    This is expected, recoverable, and should trigger fallback to
    the next configured provider rather than failing the stage.
    """


class AllProvidersExhaustedError(MAISProductionError):
    """Raised when every configured provider for a stage has failed
    or is unavailable. Unlike `ProviderUnavailableError`, this is
    terminal for the current attempt."""


class AgentExecutionError(MAISProductionError):
    """Raised when an agent fails during execution for a reason
    other than provider unavailability or input/output validation
    (e.g. an unexpected internal failure)."""


class StageDependencyError(MAISProductionError):
    """Raised when the Controller cannot build a valid execution
    plan because stage dependencies are unsatisfiable (e.g. a cycle,
    or a required upstream stage was skipped)."""


class StateStoreError(MAISProductionError):
    """Raised when persisting or loading job/stage state fails."""


class JobNotFoundError(MAISProductionError):
    """Raised when a requested job ID does not exist in the state
    store."""


class PublishingNotSupportedError(MAISProductionError):
    """Raised when the Publisher Agent is asked to publish to a
    platform whose `PublishMode` is `MANUAL` rather than `API`."""
