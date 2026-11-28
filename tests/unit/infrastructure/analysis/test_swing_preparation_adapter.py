from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest

from elliottwaver.application import TimeframeAnalysisRequest
from elliottwaver.application.temporal_market_data import TemporalCandleRecord
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Candle, CandleTemporalSemantics, Swing, SwingDirection
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


def _temporal_records(
    highs: tuple[int, ...],
    lows: tuple[int, ...],
    *,
    available_offsets_minutes: tuple[int | None, ...],
    base_time: datetime = datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
) -> tuple[TemporalCandleRecord, ...]:
    candles = _candles(highs, lows)
    shifted_candles: list[Candle] = []
    for index, candle in enumerate(candles):
        shifted_candles.append(
            Candle(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                opened_at=base_time + timedelta(hours=index),
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
        )
    candles = tuple(shifted_candles)
    assert len(candles) == len(available_offsets_minutes)

    records: list[TemporalCandleRecord] = []
    for candle, offset in zip(candles, available_offsets_minutes, strict=True):
        if offset is None:
            semantics = CandleTemporalSemantics(opened_at=candle.opened_at)
        else:
            semantics = CandleTemporalSemantics(
                opened_at=candle.opened_at,
                closed_at=candle.opened_at + timedelta(minutes=1),
                available_at=candle.opened_at + timedelta(minutes=offset),
                is_closed=True,
            )

        records.append(TemporalCandleRecord(candle=candle, temporal_semantics=semantics))

    return tuple(records)


def _swing_snapshot(swings: tuple[Swing, ...]) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            swing.id.value,
            swing.start_pivot.id.value,
            swing.end_pivot.id.value,
            swing.start_pivot.timestamp,
            swing.end_pivot.timestamp,
            swing.start_pivot.price.value,
            swing.end_pivot.price.value,
            swing.direction,
            swing.confirmed_at,
            swing.start_pivot.confirmed_at,
            swing.end_pivot.confirmed_at,
        )
        for swing in swings
    )


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


def test_prepare_swings_causal_rejects_non_utc_as_of_even_for_empty_records() -> None:
    adapter = PivotSwingPreparationAdapter()

    with pytest.raises(DomainError, match="as_of must use the UTC timezone"):
        adapter.prepare_swings_causal(
            (),
            _request(),
            as_of=datetime(2026, 7, 21, 0, 0, tzinfo=UTC).replace(tzinfo=None),
        )


def test_prepare_swings_causal_rejects_duplicate_or_non_chronological_records() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    candles = _candles(highs=(10, 11), lows=(8, 9))
    duplicate_opened_at = candles[0].opened_at

    first = TemporalCandleRecord(
        candle=candles[0],
        temporal_semantics=CandleTemporalSemantics(
            opened_at=candles[0].opened_at,
            closed_at=candles[0].opened_at + timedelta(minutes=1),
            available_at=candles[0].opened_at + timedelta(minutes=10),
            is_closed=True,
        ),
    )
    second_candle = Candle(
        symbol=candles[1].symbol,
        timeframe=candles[1].timeframe,
        opened_at=duplicate_opened_at,
        open=candles[1].open,
        high=candles[1].high,
        low=candles[1].low,
        close=candles[1].close,
        volume=candles[1].volume,
    )
    second = TemporalCandleRecord(
        candle=second_candle,
        temporal_semantics=CandleTemporalSemantics(
            opened_at=duplicate_opened_at,
            closed_at=duplicate_opened_at + timedelta(minutes=1),
            available_at=duplicate_opened_at + timedelta(minutes=12),
            is_closed=True,
        ),
    )

    with pytest.raises(DomainError, match="strictly chronological and unique"):
        adapter.prepare_swings_causal(
            (first, second),
            request,
            as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        )


def test_prepare_swings_causal_stops_at_first_unknown_candle() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14, 13),
        lows=(8, 9, 7, 10, 6, 11, 9),
        available_offsets_minutes=(10, 20, None, 30, 40, 50, 60),
    )

    swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )

    assert swings == ()


def test_prepare_swings_causal_stops_at_first_pending_candle_without_compression() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14, 13),
        lows=(8, 9, 7, 10, 6, 11, 9),
        available_offsets_minutes=(10, 20, 10_000, 30, 40, 50, 60),
    )

    swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
    )

    assert swings == ()


def test_prepare_swings_causal_sets_pivot_confirmed_at_from_full_window_max_available_at() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11, 13, 12),
        lows=(8, 9, 7, 10, 6),
        available_offsets_minutes=(300, 70, 80, 90, 100),
    )

    swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )

    assert len(swings) == 2
    expected = records[0].candle.opened_at + timedelta(minutes=300)
    assert swings[0].start_pivot.confirmed_at == expected
    assert swings[0].confirmed_at is not None
    assert swings[0].confirmed_at >= expected


def test_prepare_swings_causal_pivot_replacement_creates_new_connection_id_and_time() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    highs = (9, 12, 11, 13, 10, 11)
    lows = (8, 10, 10, 11, 7, 8)
    records = _temporal_records(
        highs=highs,
        lows=lows,
        available_offsets_minutes=(10, 20, 30, 200, 210, 220),
    )

    swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )

    assert len(swings) == 1
    assert swings[0].start_pivot.timestamp == records[3].candle.opened_at
    assert swings[0].end_pivot.timestamp == records[4].candle.opened_at

    old_start_raw = (
        f"pivot:{records[1].candle.symbol.value}:{records[1].candle.timeframe.value}:"
        f"{records[1].candle.opened_at.isoformat()}:high"
    )
    old_end_raw = (
        f"pivot:{records[4].candle.symbol.value}:{records[4].candle.timeframe.value}:"
        f"{records[4].candle.opened_at.isoformat()}:low"
    )
    old_start_id = uuid5(NAMESPACE_URL, old_start_raw)
    old_end_id = uuid5(NAMESPACE_URL, old_end_raw)
    old_swing_id = uuid5(NAMESPACE_URL, f"swing:{old_start_id}:{old_end_id}")

    assert swings[0].id.value != old_swing_id
    assert swings[0].confirmed_at is not None
    assert swings[0].start_pivot.confirmed_at is not None
    assert swings[0].end_pivot.confirmed_at is not None
    assert swings[0].confirmed_at >= swings[0].start_pivot.confirmed_at
    assert swings[0].confirmed_at >= swings[0].end_pivot.confirmed_at


def test_prepare_swings_causal_fixed_as_of_is_prefix_invariant_under_irrelevant_extension() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    base = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14, 13),
        lows=(8, 9, 7, 10, 6, 11, 9),
        available_offsets_minutes=(10, 20, 30, 40, 50, 60, 70),
    )
    extension = _temporal_records(
        highs=(15, 16),
        lows=(14, 15),
        available_offsets_minutes=(10_000, 10_001),
        base_time=base[-1].candle.opened_at + timedelta(hours=1),
    )
    extended = base + extension
    as_of = datetime(2026, 7, 21, 7, 0, tzinfo=UTC)

    base_swings = adapter.prepare_swings_causal(base, request, as_of=as_of)
    extended_swings = adapter.prepare_swings_causal(extended, request, as_of=as_of)

    assert tuple(swing.id for swing in extended_swings) == tuple(swing.id for swing in base_swings)
    assert tuple(swing.confirmed_at for swing in extended_swings) == tuple(
        swing.confirmed_at for swing in base_swings
    )


def test_prepare_swings_legacy_path_remains_unchanged() -> None:
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


def test_c01_window_maximum_of_all_available_at_sets_pivot_confirmed_at_exactly() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11, 13, 12),
        lows=(8, 9, 7, 10, 6),
        available_offsets_minutes=(500, 120, 130, 140, 150),
    )

    swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )

    assert len(swings) == 2
    expected_window_max = records[0].candle.opened_at + timedelta(minutes=500)
    assert swings[0].start_pivot.confirmed_at == expected_window_max
    assert swings[0].confirmed_at == expected_window_max


def test_c02_earlier_prefix_blockade_outside_window_sets_exact_swing_confirmation_time() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11, 13, 12),
        lows=(8, 9, 7, 10, 6),
        available_offsets_minutes=(600, 120, 130, 140, 150),
    )

    swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )

    expected_block_release = records[0].candle.opened_at + timedelta(minutes=600)
    assert len(swings) == 2
    assert swings[0].confirmed_at == expected_block_release
    assert swings[1].confirmed_at == expected_block_release


def test_c03_before_exact_and_after_blockade_release() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11, 13, 12),
        lows=(8, 9, 7, 10, 6),
        available_offsets_minutes=(600, 120, 130, 140, 150),
    )
    release = records[0].candle.opened_at + timedelta(minutes=600)

    before_swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=release - timedelta(minutes=1),
    )
    at_swings = adapter.prepare_swings_causal(records, request, as_of=release)
    after_swings = adapter.prepare_swings_causal(
        records,
        request,
        as_of=release + timedelta(minutes=1),
    )

    assert before_swings == ()
    assert len(at_swings) == 2
    assert len(after_swings) == 2
    assert at_swings[0].confirmed_at == release
    assert after_swings[0].confirmed_at == release


def test_c04_fixed_as_of_prefix_vs_full_has_full_swing_object_equality() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    prefix = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14),
        lows=(8, 9, 7, 10, 6, 11),
        available_offsets_minutes=(10, 20, 30, 40, 50, 60),
    )
    full_extension = _temporal_records(
        highs=(15, 16),
        lows=(14, 15),
        available_offsets_minutes=(5_000, 5_001),
        base_time=prefix[-1].candle.opened_at + timedelta(hours=1),
    )
    full = prefix + full_extension
    fixed_as_of = datetime(2026, 7, 21, 7, 0, tzinfo=UTC)

    prefix_swings = adapter.prepare_swings_causal(prefix, request, as_of=fixed_as_of)
    full_swings = adapter.prepare_swings_causal(full, request, as_of=fixed_as_of)

    assert len(prefix_swings) == len(full_swings)
    assert _swing_snapshot(prefix_swings) == _swing_snapshot(full_swings)


def test_c05_later_as_of_replacement_has_exact_new_id_and_confirmation_time() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(9, 12, 11, 13, 10, 11),
        lows=(8, 10, 10, 11, 7, 8),
        available_offsets_minutes=(10, 20, 30, 200, 210, 220),
    )
    late_as_of = datetime(2026, 7, 22, 0, 0, tzinfo=UTC)

    swings = adapter.prepare_swings_causal(records, request, as_of=late_as_of)

    assert len(swings) == 1
    start_raw = (
        f"pivot:{records[3].candle.symbol.value}:{records[3].candle.timeframe.value}:"
        f"{records[3].candle.opened_at.isoformat()}:high"
    )
    end_raw = (
        f"pivot:{records[4].candle.symbol.value}:{records[4].candle.timeframe.value}:"
        f"{records[4].candle.opened_at.isoformat()}:low"
    )
    expected_start_id = uuid5(NAMESPACE_URL, start_raw)
    expected_end_id = uuid5(NAMESPACE_URL, end_raw)
    expected_swing_id = uuid5(NAMESPACE_URL, f"swing:{expected_start_id}:{expected_end_id}")

    assert swings[0].id.value == expected_swing_id
    assert swings[0].start_pivot.timestamp == records[3].candle.opened_at
    assert swings[0].end_pivot.timestamp == records[4].candle.opened_at
    assert swings[0].confirmed_at == records[5].candle.opened_at + timedelta(minutes=220)


def test_c06_irrelevant_available_extension_keeps_existing_swings_unchanged() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    base = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14, 13),
        lows=(8, 9, 7, 10, 6, 11, 9),
        available_offsets_minutes=(10, 20, 30, 40, 50, 60, 70),
    )
    irrelevant = _temporal_records(
        highs=(20, 21, 22),
        lows=(19, 20, 21),
        available_offsets_minutes=(7_000, 7_001, 7_002),
        base_time=base[-1].candle.opened_at + timedelta(hours=1),
    )
    as_of = datetime(2026, 7, 21, 7, 0, tzinfo=UTC)

    before = adapter.prepare_swings_causal(base, request, as_of=as_of)
    after = adapter.prepare_swings_causal(base + irrelevant, request, as_of=as_of)

    assert len(before) == len(after)
    assert _swing_snapshot(before) == _swing_snapshot(after)


def test_c07_unknown_and_pending_without_window_compression() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()

    unknown_records = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14),
        lows=(8, 9, 7, 10, 6, 11),
        available_offsets_minutes=(10, 20, None, 30, 40, 50),
    )
    pending_records = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14),
        lows=(8, 9, 7, 10, 6, 11),
        available_offsets_minutes=(10, 20, 10_000, 30, 40, 50),
    )

    unknown_swings = adapter.prepare_swings_causal(
        unknown_records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )
    pending_swings = adapter.prepare_swings_causal(
        pending_records,
        request,
        as_of=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
    )

    assert unknown_swings == ()
    assert pending_swings == ()


def test_c08_ties_ambiguous_extrema_and_invalid_price_pairs() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()

    tie_records = _temporal_records(
        highs=(10, 12, 12, 11, 10),
        lows=(9, 10, 8, 9, 8),
        available_offsets_minutes=(10, 20, 30, 40, 50),
    )
    tie_swings = adapter.prepare_swings_causal(
        tie_records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )
    assert len(tie_swings) == 1
    assert tie_swings[0].start_pivot.timestamp == tie_records[1].candle.opened_at

    ambiguous_records = _temporal_records(
        highs=(10, 10, 10, 10, 10),
        lows=(10, 10, 10, 10, 10),
        available_offsets_minutes=(10, 20, 30, 40, 50),
    )
    ambiguous_swings = adapter.prepare_swings_causal(
        ambiguous_records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )
    assert ambiguous_swings == ()

    invalid_pair_records = _temporal_records(
        highs=(10, 11, 10, 9, 8),
        lows=(8, 9, 8, 9, 8),
        available_offsets_minutes=(10, 20, 30, 40, 50),
    )
    invalid_pair_swings = adapter.prepare_swings_causal(
        invalid_pair_records,
        request,
        as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
    )
    assert len(invalid_pair_swings) == 1
    assert invalid_pair_swings[0].start_pivot.timestamp == invalid_pair_records[1].candle.opened_at
    assert invalid_pair_swings[0].end_pivot.timestamp == invalid_pair_records[2].candle.opened_at
    assert invalid_pair_swings[0].direction is SwingDirection.DOWN


def test_c09_utc_duplicates_unsorted_symbol_and_timeframe_guards() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11),
        lows=(8, 9, 7),
        available_offsets_minutes=(10, 20, 30),
    )

    with pytest.raises(DomainError, match="as_of must use the UTC timezone"):
        adapter.prepare_swings_causal(
            records,
            request,
            as_of=datetime(2026, 7, 21, 0, 0, tzinfo=UTC).replace(tzinfo=None),
        )

    duplicate_records = (records[0], records[0])
    with pytest.raises(DomainError, match="strictly chronological and unique"):
        adapter.prepare_swings_causal(
            duplicate_records,
            request,
            as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        )

    unsorted_records = (records[1], records[0], records[2])
    with pytest.raises(DomainError, match="strictly chronological and unique"):
        adapter.prepare_swings_causal(
            unsorted_records,
            request,
            as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        )

    wrong_symbol_candle = Candle(
        symbol=Symbol("USDJPY"),
        timeframe=records[0].candle.timeframe,
        opened_at=records[0].candle.opened_at,
        open=records[0].candle.open,
        high=records[0].candle.high,
        low=records[0].candle.low,
        close=records[0].candle.close,
        volume=records[0].candle.volume,
    )
    wrong_symbol_records = (
        TemporalCandleRecord(
            candle=wrong_symbol_candle, temporal_semantics=records[0].temporal_semantics
        ),
        records[1],
    )
    with pytest.raises(DomainError, match="records symbol must match request symbol"):
        adapter.prepare_swings_causal(
            wrong_symbol_records,
            request,
            as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        )

    wrong_timeframe_candle = Candle(
        symbol=records[0].candle.symbol,
        timeframe=MarketTimeframe.FIFTEEN_MINUTES,
        opened_at=records[0].candle.opened_at,
        open=records[0].candle.open,
        high=records[0].candle.high,
        low=records[0].candle.low,
        close=records[0].candle.close,
        volume=records[0].candle.volume,
    )
    wrong_timeframe_records = (
        TemporalCandleRecord(
            candle=wrong_timeframe_candle,
            temporal_semantics=records[0].temporal_semantics,
        ),
        records[1],
    )
    with pytest.raises(DomainError, match="records timeframe must match request timeframe"):
        adapter.prepare_swings_causal(
            wrong_timeframe_records,
            request,
            as_of=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        )


def test_c10_legacy_ids_prices_directions_and_time_fields_remain_unchanged() -> None:
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
    assert swings[0].start_pivot.timestamp == candles[1].opened_at
    assert swings[0].end_pivot.timestamp == candles[2].opened_at
    assert swings[0].start_pivot.price == Price.parse(12)
    assert swings[0].end_pivot.price == Price.parse(7)
    assert swings[0].confirmed_at is None
    assert swings[0].start_pivot.confirmed_at is None
    assert swings[0].end_pivot.confirmed_at is None

    expected_start_id = uuid5(
        NAMESPACE_URL,
        (
            f"pivot:{candles[1].symbol.value}:{candles[1].timeframe.value}:"
            f"{candles[1].opened_at.isoformat()}:high"
        ),
    )
    expected_end_id = uuid5(
        NAMESPACE_URL,
        (
            f"pivot:{candles[2].symbol.value}:{candles[2].timeframe.value}:"
            f"{candles[2].opened_at.isoformat()}:low"
        ),
    )
    expected_swing_id = uuid5(NAMESPACE_URL, f"swing:{expected_start_id}:{expected_end_id}")

    assert swings[0].start_pivot.id.value == expected_start_id
    assert swings[0].end_pivot.id.value == expected_end_id
    assert swings[0].id.value == expected_swing_id


def test_c11_multi_swing_replacement_keeps_unaffected_connections_exact() -> None:
    adapter = PivotSwingPreparationAdapter()
    request = _request()
    records = _temporal_records(
        highs=(10, 12, 11, 13, 12, 14, 11, 12),
        lows=(8, 9, 7, 10, 10, 11, 6, 7),
        available_offsets_minutes=(10, 20, 30, 40, 50, 500, 70, 80),
    )
    early_as_of = records[4].candle.opened_at + timedelta(minutes=100)
    late_as_of = datetime(2026, 7, 22, 0, 0, tzinfo=UTC)

    early_swings = adapter.prepare_swings_causal(records, request, as_of=early_as_of)
    late_swings = adapter.prepare_swings_causal(records, request, as_of=late_as_of)

    assert len(early_swings) == 2
    assert len(late_swings) == 3

    unaffected_early = early_swings[0]
    unaffected_late = late_swings[0]
    assert unaffected_late.id == unaffected_early.id
    assert unaffected_late.confirmed_at == unaffected_early.confirmed_at
    assert unaffected_late.start_pivot.id == unaffected_early.start_pivot.id
    assert unaffected_late.end_pivot.id == unaffected_early.end_pivot.id

    replaced_early = early_swings[1]
    replaced_late = late_swings[1]
    assert replaced_late.id != replaced_early.id
    assert replaced_late.confirmed_at != replaced_early.confirmed_at
