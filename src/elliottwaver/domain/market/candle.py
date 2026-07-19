"""Candlestick market-data model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from elliottwaver.core.market import Symbol, Timeframe
    from elliottwaver.domain.market.price import Price


@dataclass(frozen=True, slots=True)
class Candle:
    """Immutable OHLCV candlestick."""

    symbol: Symbol
    timeframe: Timeframe
    opened_at: datetime
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Decimal

    def __post_init__(self) -> None:
        """Validate candlestick invariants."""

        if self.opened_at.tzinfo is not UTC:
            message = "Candle timestamp must use the UTC timezone"
            raise ValueError(message)

        if self.low > self.high:
            message = "Candle low must not exceed candle high"
            raise ValueError(message)

        if self.high < max(self.open, self.close):
            message = "Candle high must not be below open or close"
            raise ValueError(message)

        if self.low > min(self.open, self.close):
            message = "Candle low must not be above open or close"
            raise ValueError(message)

        if not self.volume.is_finite() or self.volume < Decimal(0):
            message = f"Invalid candle volume: {self.volume!r}"
            raise ValueError(message)

    @property
    def is_bullish(self) -> bool:
        """Return whether the candle closed above its opening price."""

        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Return whether the candle closed below its opening price."""

        return self.close < self.open

    @property
    def range(self) -> Decimal:
        """Return the complete candle price range."""

        return self.high.value - self.low.value
