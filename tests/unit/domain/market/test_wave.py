from datetime import UTC, datetime

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType


def make_pivot(*, pivot_type: PivotType, price: str, when: datetime) -> Pivot:
    return Pivot(
        id=EntityId.new(),
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=when,
        price=Price.parse(price),
        pivot_type=pivot_type,
    )


def make_swing(
    *,
    start_type: PivotType,
    end_type: PivotType,
    start_price: str,
    end_price: str,
    start_when: datetime,
    end_when: datetime,
) -> Swing:
    return Swing(
        id=EntityId.new(),
        start_pivot=make_pivot(pivot_type=start_type, price=start_price, when=start_when),
        end_pivot=make_pivot(pivot_type=end_type, price=end_price, when=end_when),
    )


def make_raw_swing(*, start_pivot: Pivot, end_pivot: Pivot) -> Swing:
    swing = object.__new__(Swing)
    object.__setattr__(swing, "id", EntityId.new())
    object.__setattr__(swing, "start_pivot", start_pivot)
    object.__setattr__(swing, "end_pivot", end_pivot)
    return swing


def test_valid_wave_collects_ordered_swings() -> None:
    bridge_pivot = make_pivot(
        pivot_type=PivotType.HIGH,
        price="1.20",
        when=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
    )
    first = Swing(
        id=EntityId.new(),
        start_pivot=make_pivot(
            pivot_type=PivotType.LOW,
            price="1.00",
            when=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        ),
        end_pivot=bridge_pivot,
    )
    second = Swing(
        id=EntityId.new(),
        start_pivot=bridge_pivot,
        end_pivot=make_pivot(
            pivot_type=PivotType.LOW,
            price="1.10",
            when=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
        ),
    )

    wave = Wave(
        id=EntityId.new(),
        swings=(first, second),
        wave_type=WaveType.IMPULSE,
        degree=WaveDegree.PRIMARY,
    )

    assert wave.symbol == first.symbol
    assert wave.timeframe == first.timeframe
    assert wave.start_timestamp == first.start_timestamp
    assert wave.end_timestamp == second.end_timestamp
    assert wave.duration == second.end_timestamp - first.start_timestamp
    assert wave.direction == first.direction
    assert wave.swings[0] is first
    assert wave.swings[1] is second


def test_rejects_empty_wave() -> None:
    with pytest.raises(DomainError, match="at least one swing"):
        Wave(id=EntityId.new(), swings=(), wave_type=WaveType.IMPULSE, degree=WaveDegree.PRIMARY)


def test_rejects_duplicate_swings() -> None:
    swing = make_swing(
        start_type=PivotType.LOW,
        end_type=PivotType.HIGH,
        start_price="1.00",
        end_price="1.20",
        start_when=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        end_when=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
    )

    with pytest.raises(DomainError, match="unique"):
        Wave(
            id=EntityId.new(),
            swings=(swing, swing),
            wave_type=WaveType.IMPULSE,
            degree=WaveDegree.PRIMARY,
        )


def test_rejects_broken_chain() -> None:
    first = Swing(
        id=EntityId.new(),
        start_pivot=make_pivot(
            pivot_type=PivotType.LOW,
            price="1.00",
            when=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        ),
        end_pivot=make_pivot(
            pivot_type=PivotType.HIGH,
            price="1.20",
            when=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        ),
    )
    second = Swing(
        id=EntityId.new(),
        start_pivot=Pivot(
            id=EntityId.new(),
            symbol=Symbol("EURUSD"),
            timeframe=Timeframe.ONE_HOUR,
            timestamp=datetime(2026, 1, 1, 0, 30, tzinfo=UTC),
            price=Price.parse("1.20"),
            pivot_type=PivotType.HIGH,
        ),
        end_pivot=make_pivot(
            pivot_type=PivotType.LOW,
            price="1.10",
            when=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
        ),
    )

    with pytest.raises(DomainError, match="chronological"):
        Wave(
            id=EntityId.new(),
            swings=(first, second),
            wave_type=WaveType.IMPULSE,
            degree=WaveDegree.PRIMARY,
        )


def test_rejects_non_alternating_directions() -> None:
    first_end_pivot = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
    )
    first = make_raw_swing(
        start_pivot=make_pivot(
            pivot_type=PivotType.LOW,
            price="1.20",
            when=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        ),
        end_pivot=first_end_pivot,
    )
    second = make_raw_swing(
        start_pivot=first_end_pivot,
        end_pivot=make_pivot(
            pivot_type=PivotType.LOW,
            price="0.80",
            when=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
        ),
    )

    with pytest.raises(DomainError, match="alternate"):
        Wave(
            id=EntityId.new(),
            swings=(first, second),
            wave_type=WaveType.IMPULSE,
            degree=WaveDegree.PRIMARY,
        )


def test_rejects_conflicting_symbol_or_timeframe() -> None:
    first = make_swing(
        start_type=PivotType.LOW,
        end_type=PivotType.HIGH,
        start_price="1.00",
        end_price="1.20",
        start_when=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        end_when=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
    )
    second = Swing(
        id=EntityId.new(),
        start_pivot=Pivot(
            id=EntityId.new(),
            symbol=Symbol("USDJPY"),
            timeframe=Timeframe.FIVE_MINUTES,
            timestamp=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
            price=Price.parse("1.30"),
            pivot_type=PivotType.HIGH,
        ),
        end_pivot=Pivot(
            id=EntityId.new(),
            symbol=Symbol("USDJPY"),
            timeframe=Timeframe.FIVE_MINUTES,
            timestamp=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
            price=Price.parse("1.10"),
            pivot_type=PivotType.LOW,
        ),
    )

    with pytest.raises(DomainError, match="same symbol"):
        Wave(
            id=EntityId.new(),
            swings=(first, second),
            wave_type=WaveType.IMPULSE,
            degree=WaveDegree.PRIMARY,
        )
