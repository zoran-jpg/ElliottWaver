"""Fibonacci ratio value object."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from elliottwaver.core.shared.errors import DomainError

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True, order=True)
class FibonacciLevel:
    """Immutable Fibonacci ratio used for projection levels."""

    ratio: Decimal

    def __post_init__(self) -> None:
        """Validate level invariants."""

        if not self.ratio.is_finite():
            message = "ratio must be finite"
            raise DomainError(message)

        if self.ratio <= _ZERO:
            message = "ratio must be greater than 0"
            raise DomainError(message)
