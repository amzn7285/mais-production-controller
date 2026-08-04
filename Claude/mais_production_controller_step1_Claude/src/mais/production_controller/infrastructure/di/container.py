"""
Service Container port.

Defines the shape a dependency-injection container must satisfy so
every other layer can request "an `IStateStore`" or "the ordered
`IProvider`s for image generation" without knowing which concrete
class or library performs the wiring. This makes the choice of DI
library (or a hand-rolled composition root) an infrastructure detail
that can be decided and changed independently of `application` and
`interfaces`.

No concrete container implementation or wiring is provided here —
that belongs to a later step, once there are real adapters to wire.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, TypeVar

TService = TypeVar("TService")

#: A zero-argument callable that produces an instance of `TService`.
#: Used by `register_factory` for implementations that must be
#: constructed fresh per resolution rather than shared as a
#: singleton.
ServiceFactory = Callable[[], TService]


class IServiceContainer(ABC):
    """Abstract contract for a dependency-injection container."""

    @abstractmethod
    def register_singleton(self, interface: type[TService], implementation: TService) -> None:
        """Register a single shared instance to be returned for
        every future `resolve(interface)` call."""
        raise NotImplementedError

    @abstractmethod
    def register_factory(
        self, interface: type[TService], factory: ServiceFactory[TService]
    ) -> None:
        """Register a factory invoked to produce a new instance on
        every `resolve(interface)` call."""
        raise NotImplementedError

    @abstractmethod
    def resolve(self, interface: type[TService]) -> TService:
        """Return an instance satisfying `interface`, per whatever
        registration (`register_singleton` or `register_factory`)
        was made for it.

        Raises `mais.production_controller.domain.exceptions
        .ConfigurationError` if `interface` was never registered.
        """
        raise NotImplementedError
