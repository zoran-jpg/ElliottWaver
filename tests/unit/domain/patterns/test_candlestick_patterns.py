from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Candle, Price
from elliottwaver.domain.patterns import (
    CandlestickPatternEngine,
    CandlestickPatternType,
    CandleTemporalSemantics,
    ConfirmationTimestampStatus,
    detect_candlestick_patterns,
    detect_candlestick_patterns_with_temporal_confirmation,
)


def _candle(
    *,
    index: int,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
) -> Candle:
    return Candle(
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        opened_at=datetime(2026, 8, 1, 0, 0, tzinfo=UTC) + timedelta(hours=index),
        open=Price.parse(open_price),
        high=Price.parse(high_price),
        low=Price.parse(low_price),
        close=Price.parse(close_price),
        volume=Decimal("100"),
    )


def _has_pattern(candles: tuple[Candle, ...], pattern_type: CandlestickPatternType) -> bool:
    patterns = detect_candlestick_patterns(candles=candles)
    return any(pattern.pattern_type is pattern_type for pattern in patterns)


def test_detect_candlestick_patterns_finds_bullish_engulfing() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )

    patterns = detect_candlestick_patterns(candles=candles)

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.pattern_type is CandlestickPatternType.BULLISH_ENGULFING
    assert pattern.candle_timestamps == (candles[0].opened_at, candles[1].opened_at)


def test_detect_candlestick_patterns_prioritizes_doji_over_hammer() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="110", low_price="100", close_price="109"),
        _candle(
            index=1, open_price="105.0", high_price="106.0", low_price="96.0", close_price="106.0"
        ),
    )

    patterns = detect_candlestick_patterns(candles=candles)

    assert [pattern.pattern_type for pattern in patterns] == [CandlestickPatternType.DRAGONFLY_DOJI]


def test_detect_candlestick_patterns_is_prefix_invariant() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
        _candle(index=2, open_price="101", high_price="104", low_price="100", close_price="103"),
        _candle(index=3, open_price="104", high_price="105", low_price="101", close_price="102"),
    )

    prefix_patterns = detect_candlestick_patterns(candles=candles[:2])
    full_patterns = detect_candlestick_patterns(candles=candles)
    prefix_last = candles[1].opened_at
    full_prefix = tuple(pattern for pattern in full_patterns if pattern.ended_at <= prefix_last)

    assert prefix_patterns == full_prefix


def test_detect_candlestick_patterns_is_deterministic() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )

    first = CandlestickPatternEngine().detect(candles)
    second = CandlestickPatternEngine().detect(candles)

    assert first == second
    assert first[0].pattern_id == second[0].pattern_id


def test_detect_candlestick_patterns_rejects_duplicate_timestamps() -> None:
    first = _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98")
    second = Candle(
        symbol=first.symbol,
        timeframe=first.timeframe,
        opened_at=first.opened_at,
        open=Price.parse("97"),
        high=Price.parse("102"),
        low=Price.parse("96"),
        close=Price.parse("101"),
        volume=Decimal("100"),
    )

    with pytest.raises(DomainError, match="timestamps must be unique"):
        detect_candlestick_patterns(candles=(first, second))


def test_bullish_engulfing_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )
    negative = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="98", high_price="101", low_price="97", close_price="99"),
    )
    boundary = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(
            index=1, open_price="97.6", high_price="100.2", low_price="97.4", close_price="100"
        ),
    )
    unfavorable_wick_too_large = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="104", low_price="96", close_price="101"),
    )
    unfavorable_wick_boundary = (
        _candle(index=0, open_price="102", high_price="103", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="105", low_price="95", close_price="102"),
    )

    assert _has_pattern(positive, CandlestickPatternType.BULLISH_ENGULFING)
    assert not _has_pattern(negative, CandlestickPatternType.BULLISH_ENGULFING)
    assert _has_pattern(boundary, CandlestickPatternType.BULLISH_ENGULFING)
    assert not _has_pattern(unfavorable_wick_too_large, CandlestickPatternType.BULLISH_ENGULFING)
    assert _has_pattern(unfavorable_wick_boundary, CandlestickPatternType.BULLISH_ENGULFING)


def test_bearish_engulfing_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="100", high_price="104", low_price="99", close_price="103"),
        _candle(index=1, open_price="104", high_price="105", low_price="98", close_price="100"),
    )
    negative = (
        _candle(index=0, open_price="100", high_price="104", low_price="99", close_price="103"),
        _candle(index=1, open_price="103", high_price="104", low_price="101", close_price="102"),
    )
    boundary = (
        _candle(index=0, open_price="98", high_price="100.2", low_price="97.8", close_price="100"),
        _candle(
            index=1, open_price="100.4", high_price="100.6", low_price="97.8", close_price="98"
        ),
    )
    unfavorable_wick_too_large = (
        _candle(index=0, open_price="98", high_price="102", low_price="97", close_price="100"),
        _candle(index=1, open_price="103", high_price="104", low_price="95", close_price="98"),
    )
    unfavorable_wick_boundary = (
        _candle(index=0, open_price="98", high_price="103", low_price="97", close_price="102"),
        _candle(index=1, open_price="103", high_price="104", low_price="94", close_price="97"),
    )

    assert _has_pattern(positive, CandlestickPatternType.BEARISH_ENGULFING)
    assert not _has_pattern(negative, CandlestickPatternType.BEARISH_ENGULFING)
    assert _has_pattern(boundary, CandlestickPatternType.BEARISH_ENGULFING)
    assert not _has_pattern(unfavorable_wick_too_large, CandlestickPatternType.BEARISH_ENGULFING)
    assert _has_pattern(unfavorable_wick_boundary, CandlestickPatternType.BEARISH_ENGULFING)


def test_hammer_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="98.5", high_price="100", low_price="90", close_price="100"),
    )
    negative = (
        _candle(index=0, open_price="97", high_price="103", low_price="90", close_price="100"),
    )
    boundary = (
        _candle(index=0, open_price="95", high_price="100", low_price="90", close_price="99"),
    )

    assert _has_pattern(positive, CandlestickPatternType.HAMMER)
    assert not _has_pattern(negative, CandlestickPatternType.HAMMER)
    assert _has_pattern(boundary, CandlestickPatternType.HAMMER)


def test_shooting_star_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="101", high_price="110", low_price="99", close_price="99.5"),
    )
    negative = (
        _candle(index=0, open_price="101", high_price="106", low_price="96", close_price="99.5"),
    )
    boundary = (
        _candle(index=0, open_price="105", high_price="110", low_price="100", close_price="101"),
    )

    assert _has_pattern(positive, CandlestickPatternType.SHOOTING_STAR)
    assert not _has_pattern(negative, CandlestickPatternType.SHOOTING_STAR)
    assert _has_pattern(boundary, CandlestickPatternType.SHOOTING_STAR)


def test_dragonfly_doji_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="100.4", high_price="101", low_price="90", close_price="100"),
    )
    negative = (
        _candle(index=0, open_price="100.6", high_price="102", low_price="90", close_price="100"),
    )
    boundary = (
        _candle(index=0, open_price="101", high_price="101", low_price="91", close_price="100"),
    )

    assert _has_pattern(positive, CandlestickPatternType.DRAGONFLY_DOJI)
    assert not _has_pattern(negative, CandlestickPatternType.DRAGONFLY_DOJI)
    assert _has_pattern(boundary, CandlestickPatternType.DRAGONFLY_DOJI)


def test_gravestone_doji_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="99.6", high_price="110", low_price="99", close_price="100"),
    )
    negative = (
        _candle(index=0, open_price="99.4", high_price="110", low_price="98", close_price="100"),
    )
    boundary = (
        _candle(index=0, open_price="99", high_price="109", low_price="99", close_price="100"),
    )

    assert _has_pattern(positive, CandlestickPatternType.GRAVESTONE_DOJI)
    assert not _has_pattern(negative, CandlestickPatternType.GRAVESTONE_DOJI)
    assert _has_pattern(boundary, CandlestickPatternType.GRAVESTONE_DOJI)


def test_tweezer_bottom_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="104", high_price="105", low_price="98", close_price="102"),
        _candle(index=1, open_price="101", high_price="104", low_price="97.8", close_price="103"),
    )
    negative = (
        _candle(index=0, open_price="104", high_price="105", low_price="98", close_price="102"),
        _candle(index=1, open_price="103", high_price="104", low_price="96.5", close_price="101"),
    )
    boundary = (
        _candle(index=0, open_price="104", high_price="105", low_price="98", close_price="102"),
        _candle(
            index=1, open_price="102.5", high_price="103.2", low_price="98.7", close_price="103"
        ),
    )

    assert _has_pattern(positive, CandlestickPatternType.TWEEZER_BOTTOM)
    assert not _has_pattern(negative, CandlestickPatternType.TWEEZER_BOTTOM)
    assert _has_pattern(boundary, CandlestickPatternType.TWEEZER_BOTTOM)


def test_tweezer_top_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="100", high_price="106", low_price="99", close_price="102"),
        _candle(index=1, open_price="103", high_price="106.3", low_price="100", close_price="101"),
    )
    negative = (
        _candle(index=0, open_price="100", high_price="106", low_price="99", close_price="102"),
        _candle(index=1, open_price="101", high_price="108", low_price="100", close_price="103"),
    )
    boundary = (
        _candle(index=0, open_price="100", high_price="106", low_price="99", close_price="102"),
        _candle(index=1, open_price="103", high_price="106.7", low_price="100", close_price="101"),
    )

    assert _has_pattern(positive, CandlestickPatternType.TWEEZER_TOP)
    assert not _has_pattern(negative, CandlestickPatternType.TWEEZER_TOP)
    assert _has_pattern(boundary, CandlestickPatternType.TWEEZER_TOP)


def test_three_line_strike_bullish_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="110", high_price="111", low_price="107", close_price="108"),
        _candle(index=1, open_price="108", high_price="109", low_price="105", close_price="106"),
        _candle(index=2, open_price="106", high_price="107", low_price="103", close_price="104"),
        _candle(index=3, open_price="103", high_price="112", low_price="102", close_price="111"),
    )
    negative = (
        _candle(index=0, open_price="110", high_price="111", low_price="107", close_price="108"),
        _candle(index=1, open_price="108", high_price="109", low_price="105", close_price="106"),
        _candle(index=2, open_price="106", high_price="107", low_price="103", close_price="104"),
        _candle(index=3, open_price="104", high_price="109", low_price="103", close_price="108"),
    )
    boundary = (
        _candle(index=0, open_price="110", high_price="111", low_price="107", close_price="108"),
        _candle(index=1, open_price="109", high_price="110", low_price="107", close_price="108"),
        _candle(index=2, open_price="109", high_price="110", low_price="107", close_price="108"),
        _candle(index=3, open_price="108", high_price="110", low_price="107", close_price="110"),
    )

    assert _has_pattern(positive, CandlestickPatternType.BULLISH_THREE_LINE_STRIKE)
    assert not _has_pattern(negative, CandlestickPatternType.BULLISH_THREE_LINE_STRIKE)
    assert _has_pattern(boundary, CandlestickPatternType.BULLISH_THREE_LINE_STRIKE)


def test_three_line_strike_bearish_positive_negative_and_boundary() -> None:
    positive = (
        _candle(index=0, open_price="100", high_price="103", low_price="99", close_price="102"),
        _candle(index=1, open_price="102", high_price="105", low_price="101", close_price="104"),
        _candle(index=2, open_price="104", high_price="107", low_price="103", close_price="106"),
        _candle(index=3, open_price="107", high_price="108", low_price="98", close_price="99"),
    )
    negative = (
        _candle(index=0, open_price="100", high_price="103", low_price="99", close_price="102"),
        _candle(index=1, open_price="102", high_price="105", low_price="101", close_price="104"),
        _candle(index=2, open_price="104", high_price="107", low_price="103", close_price="106"),
        _candle(index=3, open_price="106", high_price="107", low_price="100", close_price="101"),
    )
    boundary = (
        _candle(index=0, open_price="100", high_price="103", low_price="99", close_price="102"),
        _candle(index=1, open_price="101", high_price="103", low_price="100", close_price="102"),
        _candle(index=2, open_price="101", high_price="103", low_price="100", close_price="102"),
        _candle(index=3, open_price="102", high_price="103", low_price="100", close_price="100"),
    )

    assert _has_pattern(positive, CandlestickPatternType.BEARISH_THREE_LINE_STRIKE)
    assert not _has_pattern(negative, CandlestickPatternType.BEARISH_THREE_LINE_STRIKE)
    assert _has_pattern(boundary, CandlestickPatternType.BEARISH_THREE_LINE_STRIKE)


def test_detect_candlestick_patterns_sets_unknown_confirmation_timestamp_semantics() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )

    patterns = detect_candlestick_patterns(candles=candles)

    assert patterns[0].confirmed_at is None
    assert patterns[0].confirmation_status.value == "unknown"


def test_detect_candlestick_patterns_confirms_when_temporal_semantics_are_known() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )
    semantics = {
        candles[0].opened_at: CandleTemporalSemantics(
            opened_at=candles[0].opened_at,
            closed_at=candles[0].opened_at + timedelta(hours=1),
            available_at=candles[0].opened_at + timedelta(hours=1, minutes=5),
            is_closed=True,
        ),
        candles[1].opened_at: CandleTemporalSemantics(
            opened_at=candles[1].opened_at,
            closed_at=candles[1].opened_at + timedelta(hours=1),
            available_at=candles[1].opened_at + timedelta(hours=1, minutes=10),
            is_closed=True,
        ),
    }

    patterns = detect_candlestick_patterns_with_temporal_confirmation(
        candles=candles,
        temporal_semantics_by_opened_at=semantics,
        as_of=candles[1].opened_at + timedelta(hours=1, minutes=11),
    )

    assert patterns[0].confirmation_status is ConfirmationTimestampStatus.CONFIRMED
    assert patterns[0].confirmed_at == candles[1].opened_at + timedelta(hours=1, minutes=10)


def test_detect_candlestick_patterns_temporal_semantics_respects_as_of_analysis_time() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )
    semantics = {
        candles[0].opened_at: CandleTemporalSemantics(
            opened_at=candles[0].opened_at,
            closed_at=candles[0].opened_at + timedelta(hours=1),
            available_at=candles[0].opened_at + timedelta(hours=1, minutes=5),
            is_closed=True,
        ),
        candles[1].opened_at: CandleTemporalSemantics(
            opened_at=candles[1].opened_at,
            closed_at=candles[1].opened_at + timedelta(hours=1),
            available_at=candles[1].opened_at + timedelta(hours=1, minutes=10),
            is_closed=True,
        ),
    }

    patterns = detect_candlestick_patterns_with_temporal_confirmation(
        candles=candles,
        temporal_semantics_by_opened_at=semantics,
        as_of=candles[1].opened_at + timedelta(hours=1, minutes=9),
    )

    assert patterns[0].confirmation_status is ConfirmationTimestampStatus.PENDING
    assert patterns[0].confirmed_at is None


def test_detect_candlestick_patterns_temporal_semantics_keeps_unknown_when_data_is_incomplete() -> (
    None
):
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )
    semantics = {
        candles[0].opened_at: CandleTemporalSemantics(
            opened_at=candles[0].opened_at,
            closed_at=candles[0].opened_at + timedelta(hours=1),
            available_at=None,
            is_closed=True,
        ),
        candles[1].opened_at: CandleTemporalSemantics(
            opened_at=candles[1].opened_at,
            closed_at=candles[1].opened_at + timedelta(hours=1),
            available_at=None,
            is_closed=True,
        ),
    }

    patterns = detect_candlestick_patterns_with_temporal_confirmation(
        candles=candles,
        temporal_semantics_by_opened_at=semantics,
        as_of=candles[1].opened_at + timedelta(hours=3),
    )

    assert patterns[0].confirmation_status is ConfirmationTimestampStatus.UNKNOWN
    assert patterns[0].confirmed_at is None


def test_detect_candlestick_patterns_temporal_semantics_keeps_open_candle_unconfirmed() -> None:
    candles = (
        _candle(index=0, open_price="100", high_price="101", low_price="97", close_price="98"),
        _candle(index=1, open_price="97", high_price="102", low_price="96", close_price="101"),
    )
    semantics = {
        candles[0].opened_at: CandleTemporalSemantics(
            opened_at=candles[0].opened_at,
            closed_at=candles[0].opened_at + timedelta(hours=1),
            available_at=candles[0].opened_at + timedelta(hours=1, minutes=5),
            is_closed=True,
        ),
        candles[1].opened_at: CandleTemporalSemantics(
            opened_at=candles[1].opened_at,
            closed_at=None,
            available_at=None,
            is_closed=False,
        ),
    }

    patterns = detect_candlestick_patterns_with_temporal_confirmation(
        candles=candles,
        temporal_semantics_by_opened_at=semantics,
        as_of=candles[1].opened_at + timedelta(hours=5),
    )

    assert patterns[0].confirmation_status is ConfirmationTimestampStatus.PENDING
    assert patterns[0].confirmed_at is None


def test_temporal_semantics_requires_utc_datetimes() -> None:
    utc_plus_one = timezone(timedelta(hours=1))

    with pytest.raises(DomainError, match="timezone-aware UTC"):
        CandleTemporalSemantics(
            opened_at=datetime(2026, 8, 1, 0, 0, tzinfo=utc_plus_one),
            closed_at=datetime(2026, 8, 1, 1, 0, tzinfo=utc_plus_one),
            available_at=datetime(2026, 8, 1, 1, 5, tzinfo=utc_plus_one),
            is_closed=True,
        )


def test_three_line_strike_requires_directional_progression_not_only_candle_color() -> None:
    candles = (
        _candle(index=0, open_price="110", high_price="111", low_price="107", close_price="108"),
        _candle(index=1, open_price="108", high_price="111", low_price="106", close_price="107.9"),
        _candle(
            index=2,
            open_price="107.9",
            high_price="112",
            low_price="106",
            close_price="107.95",
        ),
        _candle(index=3, open_price="106", high_price="113", low_price="105", close_price="112"),
    )

    assert not _has_pattern(candles, CandlestickPatternType.BULLISH_THREE_LINE_STRIKE)
