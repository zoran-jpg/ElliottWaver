"""Immutable Elliott projection target."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.domain.market import Price, WaveDegree


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class ProjectionTarget:
    """A deterministic price target associated with an Elliott wave degree."""

    target_price: Price
    wave_degree: WaveDegree
    priority: int
    confidence: Decimal
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate projection-target invariants."""

        if self.priority < 1:
            message = "priority must be >= 1"
            raise DomainError(message)

        _validate_percent(self.confidence, "confidence")

        if self.description is not None and not self.description.strip():
            message = "description must not be empty when provided"
            raise DomainError(message)


def _validate_percent(value: Decimal, field_name: str) -> None:
    if not value.is_finite():
        message = f"{field_name} must be finite"
        raise DomainError(message)

    if value < _ZERO or value > _HUNDRED:
        message = f"{field_name} must be within [0, 100]"
        raise DomainError(message)
