"""Input model for deterministic projection computations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.domain.market import Price
    from elliottwaver.domain.projection.projection_direction import ProjectionDirection

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ProjectionInput:
    """Immutable reference movement and origin for a projection."""

    start_price: Price
    end_price: Price
    projection_origin: Price
    direction: ProjectionDirection

    def __post_init__(self) -> None:
        """Validate projection-input invariants."""

        _validate_price(self.start_price, "start_price")
        _validate_price(self.end_price, "end_price")
        _validate_price(self.projection_origin, "projection_origin")

        if self.start_price.value == self.end_price.value:
            message = "reference movement must not be zero"
            raise DomainError(message)

    @property
    def reference_range(self) -> Decimal:
        """Return the absolute non-zero reference movement range."""

        return abs(self.end_price.value - self.start_price.value)


def _validate_price(value: Price, field_name: str) -> None:
    if not value.value.is_finite() or value.value < _ZERO:
        message = f"{field_name} must be a valid non-negative price"
        raise DomainError(message)
