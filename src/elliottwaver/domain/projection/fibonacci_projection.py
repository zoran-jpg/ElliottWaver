"""Fibonacci projection result model."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.domain.market import Price
    from elliottwaver.domain.projection.fibonacci_level import FibonacciLevel
    from elliottwaver.domain.projection.projection_direction import ProjectionDirection

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class FibonacciProjection:
    """Immutable projection result for a specific Fibonacci level."""

    level: FibonacciLevel
    price: Price
    direction: ProjectionDirection
    reference_range: Decimal

    def __post_init__(self) -> None:
        """Validate fibonacci projection invariants."""

        if self.price.value <= _ZERO:
            message = "price must be greater than 0"
            raise DomainError(message)

        if not self.reference_range.is_finite():
            message = "reference_range must be finite"
            raise DomainError(message)

        if self.reference_range <= _ZERO:
            message = "reference_range must be greater than 0"
            raise DomainError(message)
