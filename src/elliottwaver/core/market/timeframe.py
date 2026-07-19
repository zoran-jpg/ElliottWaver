"""Supported market-data timeframes."""

from __future__ import annotations

from enum import StrEnum
from typing import Self


class Timeframe(StrEnum):
    """Supported candlestick timeframes."""

    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"

    @classmethod
    def parse(cls, value: str) -> Self:
        """Create a timeframe from a normalized string value."""

        normalized_value = value.strip().lower()

        try:
            return cls(normalized_value)
        except ValueError as error:
            message = f"Unsupported timeframe: {value!r}"
            raise ValueError(message) from error
