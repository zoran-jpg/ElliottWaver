from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.domain.market import Candle, Price


def create_candle(
    *,
    open_price: str = "100",
    high_price: str = "120",
    low_price: str = "90",
    close_price: str = "110",
    volume: str = "1000",
    opened_at: datetime | None = None,
) -> Candle:
    return Candle(
        symbol=Symbol("BTC-USDT"),
        timeframe=Timeframe.ONE_HOUR,
        opened_at=opened_at or datetime(2026, 1, 1, tzinfo=UTC),
        open=Price.parse(open_price),
        high=Price.parse(high_price),
        low=Price.parse(low_price),
        close=Price.parse(close_price),
        volume=Decimal(volume),
    )


def test_candle_exposes_market_data() -> None:
    candle = create_candle()

    assert candle.symbol == Symbol("BTC-USDT")
    assert candle.timeframe is Timeframe.ONE_HOUR
    assert candle.range == Decimal("30")
    assert candle.is_bullish
    assert not candle.is_bearish


def test_candle_recognizes_bearish_price_action() -> None:
    candle = create_candle(
        open_price="110",
        close_price="100",
    )

    assert candle.is_bearish
    assert not candle.is_bullish


@pytest.mark.parametrize(
    ("high_price", "low_price", "expected_message"),
    [
        ("105", "90", "Candle high"),
        ("120", "105", "Candle low"),
        ("80", "90", "Candle low"),
    ],
)
def test_candle_rejects_invalid_ohlc_values(
    high_price: str,
    low_price: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        create_candle(
            high_price=high_price,
            low_price=low_price,
        )


@pytest.mark.parametrize(
    "volume",
    [
        "-1",
        "NaN",
        "Infinity",
    ],
)
def test_candle_rejects_invalid_volume(volume: str) -> None:
    with pytest.raises(ValueError, match="Invalid candle volume"):
        create_candle(volume=volume)


def test_candle_requires_utc_timestamp() -> None:
    non_utc_timezone = timezone(timedelta(hours=1))

    with pytest.raises(ValueError, match="UTC timezone"):
        create_candle(
            opened_at=datetime(
                2026,
                1,
                1,
                tzinfo=non_utc_timezone,
            ),
        )
