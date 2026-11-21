"""Stateless domain service for deterministic Fibonacci price projections."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Price
from elliottwaver.domain.projection.fibonacci_projection import FibonacciProjection

if TYPE_CHECKING:
    from collections.abc import Iterable

    from elliottwaver.domain.projection.fibonacci_level import FibonacciLevel
    from elliottwaver.domain.projection.projection_input import ProjectionInput


_ZERO = Decimal("0")
_UP_DIRECTION_VALUE = "up"


@dataclass(frozen=True, slots=True)
class FibonacciProjectionEngine:
    """Create immutable FibonacciProjection results from explicit levels."""

    def project(
        self,
        projection_input: ProjectionInput,
        levels: Iterable[FibonacciLevel],
    ) -> tuple[FibonacciProjection, ...]:
        """Project target prices for the provided levels in input order."""

        reference_range = projection_input.reference_range
        origin = projection_input.projection_origin.value
        direction = projection_input.direction
        is_up_direction = direction.value == _UP_DIRECTION_VALUE

        projections: list[FibonacciProjection] = []
        for level in levels:
            target_price_value = self._calculate_target_price(
                origin=origin,
                reference_range=reference_range,
                ratio=level.ratio,
                is_up=is_up_direction,
            )

            if target_price_value <= _ZERO:
                message = "projected price must be greater than 0"
                raise DomainError(message)

            projections.append(
                FibonacciProjection(
                    level=level,
                    price=Price.parse(target_price_value),
                    direction=direction,
                    reference_range=reference_range,
                )
            )

        return tuple(projections)

    def _calculate_target_price(
        self,
        *,
        origin: Decimal,
        reference_range: Decimal,
        ratio: Decimal,
        is_up: bool,
    ) -> Decimal:
        """Calculate the target price value for one fibonacci ratio."""

        distance = reference_range * ratio
        if is_up:
            return origin + distance
        return origin - distance
