"""
Event Publisher interface.

Decouples "something happened" (a stage started, completed, failed,
was retried) from "what happens with that fact" (logging, an audit
trail, a future notification). The Controller and agents depend only
on this interface, so audit/logging destinations can be added or
changed without touching orchestration or agent code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IEventPublisher(ABC):
    """Abstract contract for publishing domain events."""

    @abstractmethod
    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        """Publish `event_name` with `payload`.

        `event_name` is a stable, dotted identifier (e.g.
        `"stage.completed"`, `"stage.retrying"`) rather than a free
        -form string, so subscribers can pattern-match reliably.
        """
        raise NotImplementedError
