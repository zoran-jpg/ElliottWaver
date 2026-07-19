"""Strongly typed entity identifiers."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class EntityId(ValueObject):
    """Stable identifier for domain entities."""

    value: UUID

    def __post_init__(self) -> None:
        if self.value.int == 0:
            message = "EntityId must not be the nil UUID."
            raise DomainError(message)

    @classmethod
    def new(cls) -> "EntityId":
        """Create a new random identifier."""
        return cls(uuid4())

    @classmethod
    def parse(cls, raw: str) -> "EntityId":
        """Parse a UUID string into an EntityId."""
        try:
            return cls(UUID(raw))
        except ValueError as exc:
            message = f"Invalid entity identifier: {raw!r}"
            raise DomainError(message) from exc

    def __str__(self) -> str:
        return str(self.value)
