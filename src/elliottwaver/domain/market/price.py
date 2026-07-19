"""Market price value object."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Self


@dataclass(frozen=True, slots=True, order=True)
class Price:
    """Non-negative finite market price."""

    value: Decimal

    def __post_init__(self) -> None:
        """Validate the price value."""

        if not self.value.is_finite() or self.value < Decimal(0):
            message = f"Invalid market price: {self.value!r}"
            raise ValueError(message)

    @classmethod
    def parse(cls, value: str | int | Decimal) -> Self:
        """Create a price from a supported input value."""

        try:
            decimal_value = Decimal(value)
        except (InvalidOperation, ValueError) as error:
            message = f"Invalid market price: {value!r}"
            raise ValueError(message) from error

        return cls(decimal_value)

    def __str__(self) -> str:
        """Return the decimal representation."""

        return str(self.value)
