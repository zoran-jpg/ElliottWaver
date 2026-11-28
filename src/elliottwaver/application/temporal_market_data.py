"""Temporal market-data contracts for analysis workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import CandleTemporalSemantics

if TYPE_CHECKING:
    from datetime import datetime

    from elliottwaver.core.market import Symbol
    from elliottwaver.core.market import Timeframe as MarketTimeframe
    from elliottwaver.domain.market import Candle


@dataclass(frozen=True, slots=True)
class TemporalCandleRecord:
    """Immutable market-data record bundling candle and temporal semantics."""

    candle: Candle
    temporal_semantics: CandleTemporalSemantics

    def __post_init__(self) -> None:
        temporal_semantics = object.__getattribute__(self, "temporal_semantics")
        if temporal_semantics is None:
            message = "Temporal semantics must be provided"
            raise DomainError(message)

        if self.candle.opened_at != temporal_semantics.opened_at:
            message = "Temporal semantics opened_at must match candle opened_at"
            raise DomainError(message)

    @classmethod
    def from_legacy_candle(cls, candle: Candle) -> TemporalCandleRecord:
        """Build a record with unknown temporal metadata for legacy candles."""

        return cls(
            candle=candle,
            temporal_semantics=CandleTemporalSemantics(opened_at=candle.opened_at),
        )


@runtime_checkable
class TemporalMarketDataProvider(Protocol):
    """Load immutable temporal candle records for a time range."""

    def load_candle_records(
        self,
        symbol: Symbol,
        timeframe: MarketTimeframe,
        start_time: datetime,
        end_time: datetime,
        maximum_candles: int | None = None,
    ) -> tuple[TemporalCandleRecord, ...]:
        """Return temporal candle records for the requested market slice."""
