from datetime import UTC, datetime
from decimal import Decimal

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing, SwingDirection


def make_pivot(
    *, entity_id: EntityId | None = None, pivot_type: PivotType, price: str, when: datetime
) -> Pivot:
    return Pivot(
        id=(entity_id or EntityId.new()),
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=when,
        price=Price.parse(price),
        pivot_type=pivot_type,
    )


def test_valid_low_to_high_swing() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t1)

    swing = Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)

    assert swing.direction == SwingDirection.UP
    assert swing.symbol == start.symbol
    assert swing.timeframe == start.timeframe
    assert swing.start_timestamp == t0
    assert swing.end_timestamp == t1
    assert swing.duration == t1 - t0
    assert swing.price_change == Decimal("1.00")
    assert swing.absolute_price_change == Decimal("1.00")


def test_valid_high_to_low_swing() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.HIGH, price="3.00", when=t0)
    end = make_pivot(pivot_type=PivotType.LOW, price="1.50", when=t1)

    swing = Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)

    assert swing.direction == SwingDirection.DOWN
    assert swing.price_change == Decimal("-1.50")
    assert swing.absolute_price_change == Decimal("1.50")


def test_rejects_identical_pivots() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    pivot = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)

    with pytest.raises(DomainError, match="must be different"):
        Swing(id=EntityId.new(), start_pivot=pivot, end_pivot=pivot)


def test_rejects_same_identity_different_object() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    entity_id = EntityId.new()
    first = make_pivot(entity_id=entity_id, pivot_type=PivotType.LOW, price="1.00", when=t0)
    second = make_pivot(entity_id=entity_id, pivot_type=PivotType.HIGH, price="2.00", when=t1)

    with pytest.raises(DomainError, match="must be different"):
        Swing(id=EntityId.new(), start_pivot=first, end_pivot=second)


def test_rejects_equal_timestamps() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t0)

    with pytest.raises(DomainError, match="start timestamp must be before"):
        Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)


def test_rejects_end_precedes_start() -> None:
    t0 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t1)

    with pytest.raises(DomainError, match="start timestamp must be before"):
        Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)


def test_rejects_different_symbols_or_timeframes() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = Pivot(
        id=EntityId.new(),
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=t0,
        price=Price.parse("1.00"),
        pivot_type=PivotType.LOW,
    )
    end = Pivot(
        id=EntityId.new(),
        symbol=Symbol("USDJPY"),
        timeframe=Timeframe.FIVE_MINUTES,
        timestamp=t1,
        price=Price.parse("2.00"),
        pivot_type=PivotType.HIGH,
    )

    with pytest.raises(DomainError, match="same symbol"):
        Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)


def test_rejects_same_pivot_types() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.LOW, price="2.00", when=t1)

    with pytest.raises(DomainError, match="must alternate"):
        Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)


def test_rejects_equal_price_movement() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="1.00", when=t1)

    with pytest.raises(DomainError, match="end price > start price"):
        Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)


def test_rejects_low_high_without_price_increase() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="2.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="1.50", when=t1)

    with pytest.raises(DomainError, match="end price > start price"):
        Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)


def test_rejects_high_low_without_price_decrease() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.HIGH, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.LOW, price="1.50", when=t1)

    with pytest.raises(DomainError, match="end price < start price"):
        Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)
