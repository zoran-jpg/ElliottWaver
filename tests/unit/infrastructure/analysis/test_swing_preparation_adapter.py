from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from elliottwaver.application import TimeframeAnalysisRequest
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.domain.market import Candle, SwingDirection
from elliottwaver.domain.market.price import Price
from elliottwaver.infrastructure.analysis import PivotSwingPreparationAdapter


def _request() -> TimeframeAnalysisRequest:
    start_time = datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    end_time = start_time + timedelta(hours=24)
    return TimeframeAnalysisRequest(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=start_time,
        end_time=end_time,
    )


def _candles(highs: tuple[int, ...], lows: tuple[int, ...]) -> tuple[Candle, ...]:
    assert len(highs) == len(lows)

    symbol = Symbol("EURUSD")
    timeframe = MarketTimeframe.ONE_HOUR
    base = datetime(2026, 7, 21, 0, 0, tzinfo=UTC)

    candles: list[Candle] = []
    for index, (high, low) in enumerate(zip(highs, lows, strict=True)):
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                opened_at=base + timedelta(hours=index),
                open=Price.parse(low),
                high=Price.parse(high),
                low=Price.parse(low),
                close=Price.parse(high),
                volume=Decimal("10"),
            )
        )

    return tuple(candles)


def test_prepare_swings_returns_empty_when_not_enough_confirmation_candles() -> None:
    adapter = PivotSwingPreparationAdapter(
        left_confirmation_candles=2, right_confirmation_candles=2
    )
    request = _request()
    candles = _candles(highs=(10, 11, 12, 11), lows=(8, 9, 10, 9))

    swings = adapter.prepare_swings(candles, request)

    assert swings == ()


def test_prepare_swings_builds_alternating_swings_from_confirmed_pivots() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    candles = _candles(
        highs=(10, 12, 11, 13, 12, 14, 13),
        lows=(8, 9, 7, 10, 6, 11, 9),
    )

    swings = adapter.prepare_swings(candles, request)

    assert len(swings) == 4
    assert tuple(swing.direction for swing in swings) == (
        SwingDirection.DOWN,
        SwingDirection.UP,
        SwingDirection.DOWN,
        SwingDirection.UP,
    )


def test_prepare_swings_uses_leftmost_tie_break_for_equal_window_highs() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    candles = _candles(
        highs=(10, 12, 12, 11, 10),
        lows=(9, 10, 8, 9, 8),
    )

    swings = adapter.prepare_swings(candles, request)

    assert len(swings) == 1
    assert swings[0].start_pivot.timestamp == candles[1].opened_at
    assert swings[0].end_pivot.timestamp == candles[2].opened_at


def test_prepare_swings_keeps_more_extreme_pivot_for_consecutive_same_type() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    candles = _candles(
        highs=(9, 12, 11, 13, 10, 11),
        lows=(8, 10, 10, 11, 7, 8),
    )

    swings = adapter.prepare_swings(candles, request)

    assert len(swings) == 1
    assert swings[0].start_pivot.timestamp == candles[3].opened_at
    assert swings[0].start_pivot.price == Price.parse(13)
    assert swings[0].end_pivot.timestamp == candles[4].opened_at


def test_prepare_swings_ignores_unconfirmed_right_edge_extreme() -> None:
    adapter = PivotSwingPreparationAdapter(
        left_confirmation_candles=1, right_confirmation_candles=1
    )
    request = _request()
    candles = _candles(
        highs=(10, 13, 11, 14, 12, 20),
        lows=(8, 9, 7, 10, 6, 19),
    )

    swings = adapter.prepare_swings(candles, request)

    assert len(swings) == 3
    assert swings[-1].end_pivot.timestamp != candles[-1].opened_at


def test_prepare_swings_returns_empty_for_sideways_flat_market_data() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    candles = _candles(
        highs=(10, 10, 10, 10, 10),
        lows=(10, 10, 10, 10, 10),
    )

    swings = adapter.prepare_swings(candles, request)

    assert swings == ()
