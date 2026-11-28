from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing, SwingDirection


def make_pivot(
    *,
    entity_id: EntityId | None = None,
    pivot_type: PivotType,
    price: str,
    when: datetime,
    confirmed_at: datetime | None = None,
) -> Pivot:
    return Pivot(
        id=(entity_id or EntityId.new()),
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=when,
        price=Price.parse(price),
        pivot_type=pivot_type,
        confirmed_at=confirmed_at,
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


def test_is_confirmed_defaults_false_without_confirmed_at() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t1)
    swing = Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)

    assert not swing.is_confirmed(as_of=t1)


def test_valid_confirmed_swing() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 0, 10, tzinfo=UTC),
    )
    end_confirmed = datetime(2026, 1, 1, 1, 15, tzinfo=UTC)
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=end_confirmed,
    )
    swing = Swing(
        id=EntityId.new(),
        start_pivot=start,
        end_pivot=end,
        confirmed_at=datetime(2026, 1, 1, 1, 20, tzinfo=UTC),
    )

    assert not swing.is_confirmed(as_of=datetime(2026, 1, 1, 1, 19, tzinfo=UTC))
    assert swing.is_confirmed(as_of=datetime(2026, 1, 1, 1, 20, tzinfo=UTC))
    assert swing.is_confirmed(as_of=datetime(2026, 1, 1, 1, 21, tzinfo=UTC))


def test_rejects_confirmed_at_before_end_extremum() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 0, 10, tzinfo=UTC),
    )
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
    )

    with pytest.raises(DomainError, match="must not be before the end pivot extremum"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 0, 59, tzinfo=UTC),
        )


def test_rejects_confirmed_at_without_confirmed_end_pivot() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t1)

    with pytest.raises(DomainError, match="requires confirmed start and end pivots"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
        )


def test_rejects_confirmed_at_when_both_pivots_are_unconfirmed() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t1)

    with pytest.raises(DomainError, match="requires confirmed start and end pivots"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
        )


def test_rejects_confirmed_at_when_only_start_pivot_is_confirmed() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 0, 10, tzinfo=UTC),
    )
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t1)

    with pytest.raises(DomainError, match="requires confirmed start and end pivots"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
        )


def test_rejects_confirmed_at_when_only_end_pivot_is_confirmed() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
    )

    with pytest.raises(DomainError, match="requires confirmed start and end pivots"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
        )


def test_rejects_confirmed_at_before_end_pivot_confirmation() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 0, 10, tzinfo=UTC),
    )
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=datetime(2026, 1, 1, 1, 20, tzinfo=UTC),
    )

    with pytest.raises(DomainError, match="at or after both pivot confirmations"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 1, 15, tzinfo=UTC),
        )


def test_rejects_confirmed_at_before_start_pivot_confirmation_even_if_after_end() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 1, 25, tzinfo=UTC),
    )
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
    )

    with pytest.raises(DomainError, match="at or after both pivot confirmations"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 1, 20, tzinfo=UTC),
        )


def test_accepts_confirmed_at_equal_to_max_endpoint_confirmation_time() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 1, 20, tzinfo=UTC),
    )
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=datetime(2026, 1, 1, 1, 15, tzinfo=UTC),
    )

    swing = Swing(
        id=EntityId.new(),
        start_pivot=start,
        end_pivot=end,
        confirmed_at=datetime(2026, 1, 1, 1, 20, tzinfo=UTC),
    )

    assert swing.is_confirmed(as_of=datetime(2026, 1, 1, 1, 20, tzinfo=UTC))


def test_rejects_non_utc_confirmed_at() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 0, 10, tzinfo=UTC),
    )
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
    )

    with pytest.raises(DomainError, match="UTC timezone"):
        Swing(
            id=EntityId.new(),
            start_pivot=start,
            end_pivot=end,
            confirmed_at=datetime(2026, 1, 1, 1, 30, tzinfo=timezone(timedelta(hours=1))),
        )


def test_is_confirmed_rejects_invalid_as_of_timezone() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_type=PivotType.LOW,
        price="1.00",
        when=t0,
        confirmed_at=datetime(2026, 1, 1, 0, 10, tzinfo=UTC),
    )
    end = make_pivot(
        pivot_type=PivotType.HIGH,
        price="2.00",
        when=t1,
        confirmed_at=datetime(2026, 1, 1, 1, 10, tzinfo=UTC),
    )
    swing = Swing(
        id=EntityId.new(),
        start_pivot=start,
        end_pivot=end,
        confirmed_at=datetime(2026, 1, 1, 1, 20, tzinfo=UTC),
    )
    naive_as_of = datetime(2026, 1, 1, 1, 20, tzinfo=UTC).replace(tzinfo=None)

    with pytest.raises(DomainError, match="as_of must use the UTC timezone"):
        swing.is_confirmed(as_of=naive_as_of)


def test_is_confirmed_rejects_invalid_as_of_timezone_when_confirmed_at_is_none() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    start = make_pivot(pivot_type=PivotType.LOW, price="1.00", when=t0)
    end = make_pivot(pivot_type=PivotType.HIGH, price="2.00", when=t1)
    swing = Swing(id=EntityId.new(), start_pivot=start, end_pivot=end)
    naive_as_of = datetime(2026, 1, 1, 1, 30, tzinfo=UTC).replace(tzinfo=None)

    with pytest.raises(DomainError, match="as_of must use the UTC timezone"):
        swing.is_confirmed(as_of=naive_as_of)
