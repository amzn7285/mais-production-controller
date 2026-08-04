"""
Production Agent interface.

Every concrete agent (Scene, Voice, Metadata, Thumbnail, Image,
Video, Lip Sync, Merge, QC, Publisher) implements `IProductionAgent`.
The Controller depends on this interface only — never on a concrete
agent class — so agents can be added, replaced, or independently
tested without touching the Controller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mais.production_controller.domain.enums import AgentType
from mais.production_controller.domain.models import AgentRequest, AgentResponse


class IProductionAgent(ABC):
    """Abstract contract for a single production agent.

    The method breakdown mirrors the agent lifecycle defined for
    MAIS: validate input, execute (which internally selects a
    provider and produces output), validate output, and return a
    standard response. `execute` is the single entry point the
    Controller calls; `validate_input` and `validate_output` are
    exposed separately so implementations can be unit tested in
    isolation from provider execution.
    """

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """The `AgentType` this instance implements."""
        raise NotImplementedError

    @abstractmethod
    async def validate_input(self, request: AgentRequest) -> None:
        """Validate `request` against this agent's contract.

        Implementations raise `mais.production_controller.domain
        .exceptions.ValidationError` on failure; they do not return
        a boolean, so validation failures cannot be silently
        ignored by a caller that forgets to check a return value.
        """
        raise NotImplementedError

    @abstractmethod
    async def validate_output(self, response: AgentResponse) -> None:
        """Validate a produced `AgentResponse` before it is
        returned to the Controller. Raises `ValidationError` on
        failure."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Run this agent for `request` and return a standard
        `AgentResponse`.

        Implementations are expected to internally: validate input,
        select a provider (via an injected provider-selection
        collaborator), execute against it, validate output, and
        return the response — never raising for an expected,
        retriable failure (that belongs in `AgentResponse.error`),
        reserving raised exceptions for unexpected failures the
        Controller's retry policy should also be able to observe.
        """
        raise NotImplementedError
