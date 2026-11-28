"""Swing domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from elliottwaver.core.shared.entity import Entity
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market.pivot import PivotType

if TYPE_CHECKING:
    from decimal import Decimal

    from elliottwaver.core.market import Symbol, Timeframe
    from elliottwaver.domain.market.pivot import Pivot


class SwingDirection(StrEnum):
    """Directional movement implied by two pivots."""

    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, eq=False, slots=True)
class Swing(Entity[EntityId]):
    """A confirmed movement between two alternating pivots."""

    id: EntityId
    start_pivot: Pivot
    end_pivot: Pivot
    confirmed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate swing invariants computed from start and end pivots."""

        self._validate_pivot_pair()
        self._validate_price_movement()
        self._validate_confirmation_timestamp()

    def _validate_pivot_pair(self) -> None:
        """Validate base relational constraints between both pivots."""

        if self.start_pivot is self.end_pivot or self.start_pivot.id == self.end_pivot.id:
            message = "Swing pivots must be different"
            raise DomainError(message)

        if self.start_pivot.timestamp >= self.end_pivot.timestamp:
            message = "Swing start timestamp must be before end timestamp"
            raise DomainError(message)

        if self.start_pivot.symbol != self.end_pivot.symbol:
            message = "Swing pivots must share the same symbol"
            raise DomainError(message)

        if self.start_pivot.timeframe != self.end_pivot.timeframe:
            message = "Swing pivots must share the same timeframe"
            raise DomainError(message)

        if self.start_pivot.pivot_type == self.end_pivot.pivot_type:
            message = "Swing pivot types must alternate"
            raise DomainError(message)

    def _validate_price_movement(self) -> None:
        """Validate directional price movement based on pivot types."""

        start_price = self.start_pivot.price.value
        end_price = self.end_pivot.price.value

        if self.start_pivot.pivot_type is self.end_pivot.pivot_type:
            message = "Swing pivot types must alternate"
            raise DomainError(message)

        if (
            self.start_pivot.pivot_type is PivotType.LOW
            and self.end_pivot.pivot_type is PivotType.HIGH
        ):
            if end_price <= start_price:
                message = "LOW->HIGH swing must have end price > start price"
                raise DomainError(message)
        elif (
            self.start_pivot.pivot_type is PivotType.HIGH
            and self.end_pivot.pivot_type is PivotType.LOW
        ):
            if end_price >= start_price:
                message = "HIGH->LOW swing must have end price < start price"
                raise DomainError(message)
        else:
            message = "Invalid pivot type combination for swing"
            raise DomainError(message)

    def _validate_confirmation_timestamp(self) -> None:
        """Validate optional confirmation timestamp against endpoint constraints."""

        if self.confirmed_at is None:
            return

        if self.confirmed_at.tzinfo is None:
            message = "Swing confirmed_at must use the UTC timezone"
            raise DomainError(message)

        if self.confirmed_at.tzinfo != UTC:
            message = "Swing confirmed_at must use the UTC timezone"
            raise DomainError(message)

        if self.confirmed_at < self.end_pivot.timestamp:
            message = "Swing confirmed_at must not be before the end pivot extremum"
            raise DomainError(message)

        start_confirmed_at = self.start_pivot.confirmed_at
        end_confirmed_at = self.end_pivot.confirmed_at
        if start_confirmed_at is None or end_confirmed_at is None:
            message = "Swing confirmed_at requires confirmed start and end pivots"
            raise DomainError(message)

        endpoint_confirmation_floor = max(start_confirmed_at, end_confirmed_at)
        if self.confirmed_at < endpoint_confirmation_floor:
            message = "Swing confirmed_at must be at or after both pivot confirmations"
            raise DomainError(message)

    @property
    def direction(self) -> SwingDirection:
        """Return the derived direction of the swing."""

        if self.start_pivot.pivot_type is PivotType.LOW:
            return SwingDirection.UP
        return SwingDirection.DOWN

    @property
    def symbol(self) -> Symbol:
        """Return the swing symbol."""

        return self.start_pivot.symbol

    @property
    def timeframe(self) -> Timeframe:
        """Return the swing timeframe."""

        return self.start_pivot.timeframe

    @property
    def start_timestamp(self) -> datetime:
        """Return the start timestamp."""

        return self.start_pivot.timestamp

    @property
    def end_timestamp(self) -> datetime:
        """Return the end timestamp."""

        return self.end_pivot.timestamp

    @property
    def duration(self) -> timedelta:
        """Return the duration between both pivots."""

        return self.end_pivot.timestamp - self.start_pivot.timestamp

    @property
    def price_change(self) -> Decimal:
        """Return the signed price change between pivots."""

        return self.end_pivot.price.value - self.start_pivot.price.value

    @property
    def absolute_price_change(self) -> Decimal:
        """Return the non-negative absolute price change."""

        return abs(self.price_change)

    def is_confirmed(self, *, as_of: datetime) -> bool:
        """Return whether this swing is confirmed as of the provided timestamp."""

        if as_of.tzinfo is None:
            message = "as_of must use the UTC timezone"
            raise DomainError(message)

        if as_of.tzinfo != UTC:
            message = "as_of must use the UTC timezone"
            raise DomainError(message)

        return self.confirmed_at is not None and as_of >= self.confirmed_at
