from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Price
from elliottwaver.domain.projection import (
    FibonacciLevel,
    FibonacciProjection,
    ProjectionDirection,
    ProjectionInput,
)


def test_fibonacci_projection_valid_construction_and_equality() -> None:
    first = FibonacciProjection(
        level=FibonacciLevel(ratio=Decimal("1.618")),
        price=Price.parse("150"),
        direction=ProjectionDirection.UP,
        reference_range=Decimal("20"),
    )
    second = FibonacciProjection(
        level=FibonacciLevel(ratio=Decimal("1.618")),
        price=Price.parse("150"),
        direction=ProjectionDirection.UP,
        reference_range=Decimal("20"),
    )

    assert first == second


def test_fibonacci_projection_is_frozen() -> None:
    projection = FibonacciProjection(
        level=FibonacciLevel(ratio=Decimal("1.272")),
        price=Price.parse("140"),
        direction=ProjectionDirection.DOWN,
        reference_range=Decimal("15"),
    )

    with pytest.raises(FrozenInstanceError):
        projection.__setattr__("reference_range", Decimal("10"))


@pytest.mark.parametrize(
    ("price_value", "message"),
    [
        ("0", "price must be greater than 0"),
    ],
)
def test_fibonacci_projection_rejects_invalid_price(
    price_value: str,
    message: str,
) -> None:
    with pytest.raises(DomainError, match=message):
        FibonacciProjection(
            level=FibonacciLevel(ratio=Decimal("1.0")),
            price=Price.parse(price_value),
            direction=ProjectionDirection.UP,
            reference_range=Decimal("10"),
        )


@pytest.mark.parametrize(
    ("reference_range", "message"),
    [
        (Decimal("0"), "reference_range must be greater than 0"),
        (Decimal("-1"), "reference_range must be greater than 0"),
        (Decimal("NaN"), "reference_range must be finite"),
    ],
)
def test_fibonacci_projection_rejects_invalid_reference_range(
    reference_range: Decimal,
    message: str,
) -> None:
    with pytest.raises(DomainError, match=message):
        FibonacciProjection(
            level=FibonacciLevel(ratio=Decimal("1.0")),
            price=Price.parse("130"),
            direction=ProjectionDirection.UP,
            reference_range=reference_range,
        )


def test_projection_package_exports() -> None:
    assert FibonacciLevel.__name__ == "FibonacciLevel"
    assert FibonacciProjection.__name__ == "FibonacciProjection"
    assert ProjectionDirection.__name__ == "ProjectionDirection"
    assert ProjectionInput.__name__ == "ProjectionInput"
