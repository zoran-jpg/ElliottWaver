from datetime import UTC, datetime

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType


def make_pivot(
    *, pivot_type: PivotType, price: str = "1.00", when: datetime | None = None
) -> Pivot:
    when = when or datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    return Pivot(
        id=EntityId.new(),
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=when,
        price=Price.parse(price),
        pivot_type=pivot_type,
    )


def test_valid_high_pivot() -> None:
    pivot = make_pivot(pivot_type=PivotType.HIGH, price="1.2000")

    assert pivot.pivot_type == PivotType.HIGH
    assert str(pivot.price) == "1.2000"
    assert pivot.symbol.value == "EURUSD"
    assert pivot.timeframe == Timeframe.ONE_HOUR


def test_valid_low_pivot() -> None:
    pivot = make_pivot(pivot_type=PivotType.LOW, price="0.8000")
    assert pivot.pivot_type == PivotType.LOW


def test_identity_behavior_is_entity_like() -> None:
    entity_id = EntityId.new()
    first = Pivot(
        id=entity_id,
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        price=Price.parse("1.00"),
        pivot_type=PivotType.HIGH,
    )
    second = Pivot(
        id=entity_id,
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        price=Price.parse("2.00"),
        pivot_type=PivotType.LOW,
    )

    assert first == second


def test_rejects_naive_datetime() -> None:
    with pytest.raises(DomainError, match="UTC timezone"):
        Pivot(
            id=EntityId.new(),
            symbol=Symbol("EURUSD"),
            timeframe=Timeframe.ONE_HOUR,
            timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=UTC).replace(tzinfo=None),
            price=Price.parse("1.00"),
            pivot_type=PivotType.HIGH,
        )
