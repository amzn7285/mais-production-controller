"""Base model definitions for all MAIS data contracts.

These base classes centralize validation and serialization behavior so every
contract shares consistent enterprise semantics. They contain no business logic.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class MaisBaseModel(BaseModel):
    """Mutable base class for MAIS data contracts.

    Enforces strict field validation, whitespace trimming, and assignment
    validation. Provides stable JSON serialization helpers.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
        extra="forbid",
        use_enum_values=False,
        frozen=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return self.model_dump(mode="json", by_alias=True)

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize to a JSON string."""
        return self.model_dump_json(by_alias=True, indent=indent)


class MaisImmutableModel(MaisBaseModel):
    """Immutable variant of the MAIS base model.

    Use for value objects and frozen contracts (e.g. MasterProduction,
    configuration, results, artifacts) that must not change after creation.
    """

    model_config = ConfigDict(frozen=True)