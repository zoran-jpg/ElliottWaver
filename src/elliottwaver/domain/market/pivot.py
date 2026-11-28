"""Pivot domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from elliottwaver.core.shared.entity import Entity
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId

if TYPE_CHECKING:
    from elliottwaver.core.market import Symbol, Timeframe
    from elliottwaver.domain.market.price import Price


class PivotType(StrEnum):
    """Type of confirmed pivot."""

    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True, eq=False, slots=True)
class Pivot(Entity[EntityId]):
    """A confirmed market turning point."""

    id: EntityId
    symbol: Symbol
    timeframe: Timeframe
    timestamp: datetime
    price: Price
    pivot_type: PivotType
    confirmed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate pivot invariants at construction."""

        if self.timestamp.tzinfo is None:
            message = "Pivot timestamp must use the UTC timezone"
            raise DomainError(message)

        if self.timestamp.tzinfo != UTC:
            message = "Pivot timestamp must use the UTC timezone"
            raise DomainError(message)

        if self.pivot_type not in PivotType:
            message = "pivot_type must be a PivotType"
            raise DomainError(message)

        if self.confirmed_at is None:
            return

        if self.confirmed_at.tzinfo is None:
            message = "Pivot confirmed_at must use the UTC timezone"
            raise DomainError(message)

        if self.confirmed_at.tzinfo != UTC:
            message = "Pivot confirmed_at must use the UTC timezone"
            raise DomainError(message)

        if self.confirmed_at < self.timestamp:
            message = "Pivot confirmed_at must not be before the extremum timestamp"
            raise DomainError(message)

    @property
    def extremum_at(self) -> datetime:
        """Alias for the pivot extremum timestamp."""

        return self.timestamp

    def is_confirmed(self, *, as_of: datetime) -> bool:
        """Return whether this pivot is confirmed as of the provided timestamp."""

        if as_of.tzinfo is None:
            message = "as_of must use the UTC timezone"
            raise DomainError(message)

        if as_of.tzinfo != UTC:
            message = "as_of must use the UTC timezone"
            raise DomainError(message)

        return self.confirmed_at is not None and as_of >= self.confirmed_at
