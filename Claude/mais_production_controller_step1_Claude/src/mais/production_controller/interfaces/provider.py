"""
Provider interface.

An `IProvider` wraps a single external or local capability (a
specific text-generation API, a specific TTS engine, a specific
image-generation API, etc.). Agents depend on `IProvider` and a
provider-selection collaborator (see `IProviderResolver` below) —
never on a named provider class — so the fallback-provider pattern
from the architecture review (try provider A, fall back to B, then
C) is implementable purely by supplying an ordered list of
`IProvider` instances, with no changes to agent code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mais.production_controller.domain.enums import ProviderCapability


class IProvider(ABC):
    """Abstract contract for a single external or local capability
    provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable, unique identifier for this provider, used in
        config, logs, and `AgentResponse.provider_used`."""
        raise NotImplementedError

    @property
    @abstractmethod
    def capability(self) -> ProviderCapability:
        """The single capability this provider offers."""
        raise NotImplementedError

    @abstractmethod
    async def is_available(self) -> bool:
        """Cheap, side-effect-free check of whether this provider
        can currently be used (e.g. credentials present, known
        rate-limit window not exhausted). Used by an
        `IProviderResolver` to skip known-bad providers before
        spending a full `invoke` attempt."""
        raise NotImplementedError

    @abstractmethod
    async def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute this provider's capability against `payload` and
        return a raw result payload.

        Raises `mais.production_controller.domain.exceptions
        .ProviderUnavailableError` for expected, retriable failure
        modes (rate limited, transient network error) so callers can
        distinguish "try the next provider" from an unexpected
        failure.
        """
        raise NotImplementedError


class IProviderResolver(ABC):
    """Selects a usable `IProvider` from a configured, ordered
    candidate list.

    Separating this from `IProvider` itself is what lets the
    fallback-order logic (try each candidate in priority order,
    skipping unavailable ones) live in exactly one place, shared by
    every agent, instead of being reimplemented per agent.
    """

    @abstractmethod
    async def resolve(
        self, capability: ProviderCapability, candidates: tuple[IProvider, ...]
    ) -> IProvider:
        """Return the first available provider from `candidates` for
        `capability`, in the order supplied.

        Raises `mais.production_controller.domain.exceptions
        .AllProvidersExhaustedError` if none are available.
        """
        raise NotImplementedError
