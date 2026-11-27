from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from elliottwaver.application.support_resistance import (
    DEFAULT_MAX_ZONE_WIDTH_RATIO,
    derive_support_resistance_zones,
)
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import Candle, Pivot, PivotType, Price, Swing

_SYMBOL = Symbol("EURUSD")
_TIMEFRAME = MarketTimeframe.ONE_HOUR


def _candle(*, hour: int, open_price: str, high: str, low: str, close: str) -> Candle:
    return Candle(
        symbol=_SYMBOL,
        timeframe=_TIMEFRAME,
        opened_at=datetime(2026, 7, 21, hour, 0, tzinfo=UTC),
        open=Price.parse(open_price),
        high=Price.parse(high),
        low=Price.parse(low),
        close=Price.parse(close),
        volume=Decimal("10"),
    )


def _pivot(*, suffix: int, hour: int, price: str, pivot_type: PivotType) -> Pivot:
    return Pivot(
        id=EntityId.parse(f"12345678-1234-5678-1234-5678999999{suffix:02d}"),
        symbol=_SYMBOL,
        timeframe=_TIMEFRAME,
        timestamp=datetime(2026, 7, 21, hour, 0, tzinfo=UTC),
        price=Price.parse(price),
        pivot_type=pivot_type,
    )


def _swing(*, suffix: int, start: Pivot, end: Pivot) -> Swing:
    return Swing(
        id=EntityId.parse(f"12345678-1234-5678-1234-5678999998{suffix:02d}"),
        start_pivot=start,
        end_pivot=end,
    )


def test_derive_support_resistance_zones_uses_ohlc_bounds_from_confirmed_pivots() -> None:
    candles = (
        _candle(hour=0, open_price="100", high="110", low="95", close="105"),
        _candle(hour=1, open_price="106", high="115", low="104", close="112"),
    )
    low_pivot = _pivot(suffix=1, hour=0, price="95", pivot_type=PivotType.LOW)
    high_pivot = _pivot(suffix=2, hour=1, price="115", pivot_type=PivotType.HIGH)
    swings = (_swing(suffix=1, start=low_pivot, end=high_pivot),)

    zones = derive_support_resistance_zones(candles=candles, swings=swings)

    assert [zone.zone_type for zone in zones] == ["support", "resistance"]
    assert zones[0].lower_price == Decimal("95")
    assert zones[0].upper_price == Decimal("100")
    assert zones[1].lower_price == Decimal("112")
    assert zones[1].upper_price == Decimal("115")


def test_derive_support_resistance_zones_merges_overlapping_zones_and_counts_touches() -> None:
    candles = (
        _candle(hour=0, open_price="100", high="108", low="95", close="104"),
        _candle(hour=1, open_price="105", high="112", low="103", close="110"),
        _candle(hour=2, open_price="101", high="109", low="97", close="103"),
    )
    low_a = _pivot(suffix=3, hour=0, price="95", pivot_type=PivotType.LOW)
    high_a = _pivot(suffix=4, hour=1, price="112", pivot_type=PivotType.HIGH)
    low_b = _pivot(suffix=5, hour=2, price="97", pivot_type=PivotType.LOW)
    swings = (
        _swing(suffix=2, start=low_a, end=high_a),
        _swing(suffix=3, start=high_a, end=low_b),
    )

    zones = derive_support_resistance_zones(
        candles=candles,
        swings=swings,
        max_zone_width_ratio=Decimal("0.20"),
    )
    support = zones[0]

    assert support.zone_type == "support"
    assert support.lower_price == Decimal("95")
    assert support.upper_price == Decimal("101")
    assert support.touch_count == 2
    assert len(support.pivot_ids) == 2


def test_derive_support_resistance_zones_dedupes_reused_pivots_and_orders_stably() -> None:
    candles = (
        _candle(hour=0, open_price="85", high="90", low="80", close="86"),
        _candle(hour=1, open_price="106", high="115", low="104", close="112"),
        _candle(hour=2, open_price="100", high="110", low="95", close="102"),
    )
    low_early = _pivot(suffix=6, hour=0, price="80", pivot_type=PivotType.LOW)
    high_mid = _pivot(suffix=7, hour=1, price="115", pivot_type=PivotType.HIGH)
    low_late = _pivot(suffix=8, hour=2, price="95", pivot_type=PivotType.LOW)
    swings = (
        _swing(suffix=4, start=low_early, end=high_mid),
        _swing(suffix=5, start=high_mid, end=low_late),
    )

    zones = derive_support_resistance_zones(candles=candles, swings=swings)

    assert [zone.zone_type for zone in zones] == ["support", "support", "resistance"]
    assert zones[0].lower_price == Decimal("80")
    assert zones[1].lower_price == Decimal("95")
    assert zones[2].touch_count == 1


def test_derive_support_resistance_zones_ignores_pivots_without_matching_candle_timestamp() -> None:
    candles = (
        _candle(hour=0, open_price="100", high="106", low="95", close="103"),
        _candle(hour=1, open_price="101", high="107", low="96", close="104"),
    )
    low_pivot = _pivot(suffix=9, hour=0, price="95", pivot_type=PivotType.LOW)
    # Missing candle for hour=3, so this pivot must not become a zone.
    high_future = _pivot(suffix=10, hour=3, price="120", pivot_type=PivotType.HIGH)
    swings = (_swing(suffix=6, start=low_pivot, end=high_future),)

    zones = derive_support_resistance_zones(candles=candles, swings=swings)

    assert [zone.zone_type for zone in zones] == ["support"]


def test_derive_support_resistance_zones_preserves_single_zone_ohlc_bounds() -> None:
    candles = (
        _candle(hour=0, open_price="100", high="150", low="90", close="140"),
        _candle(hour=1, open_price="110", high="112", low="100", close="101"),
    )
    high_pivot = _pivot(suffix=11, hour=0, price="150", pivot_type=PivotType.HIGH)
    low_pivot = _pivot(suffix=12, hour=1, price="100", pivot_type=PivotType.LOW)
    swings = (_swing(suffix=7, start=high_pivot, end=low_pivot),)

    zones = derive_support_resistance_zones(
        candles=candles,
        swings=swings,
        max_zone_width_ratio=Decimal("0.02"),
    )

    resistance = next(zone for zone in zones if zone.zone_type == "resistance")
    assert resistance.lower_price == Decimal("140")
    assert resistance.upper_price == Decimal("150")


def test_derive_support_resistance_zones_stops_transitive_merge_when_width_cap_exceeded() -> None:
    candles = (
        _candle(hour=0, open_price="99", high="103", low="97", close="101"),
        _candle(hour=1, open_price="100", high="104", low="98", close="102"),
        _candle(hour=2, open_price="101", high="105", low="99", close="103"),
        _candle(hour=3, open_price="102", high="106", low="100", close="104"),
    )
    low_a = _pivot(suffix=13, hour=0, price="97", pivot_type=PivotType.LOW)
    high_a = _pivot(suffix=14, hour=1, price="104", pivot_type=PivotType.HIGH)
    low_b = _pivot(suffix=15, hour=2, price="99", pivot_type=PivotType.LOW)
    high_b = _pivot(suffix=16, hour=3, price="106", pivot_type=PivotType.HIGH)
    swings = (
        _swing(suffix=8, start=low_a, end=high_a),
        _swing(suffix=9, start=high_a, end=low_b),
        _swing(suffix=10, start=low_b, end=high_b),
    )

    zones = derive_support_resistance_zones(
        candles=candles,
        swings=swings,
        max_zone_width_ratio=DEFAULT_MAX_ZONE_WIDTH_RATIO,
    )

    supports = [zone for zone in zones if zone.zone_type == "support"]
    assert len(supports) >= 2
