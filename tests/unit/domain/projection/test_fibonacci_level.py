from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.projection import FibonacciLevel


def test_fibonacci_level_valid_construction_and_equality() -> None:
    first = FibonacciLevel(ratio=Decimal("0.618"))
    second = FibonacciLevel(ratio=Decimal("0.618"))

    assert first == second
    assert first.ratio == Decimal("0.618")


def test_fibonacci_level_is_frozen() -> None:
    level = FibonacciLevel(ratio=Decimal("1.618"))

    with pytest.raises(FrozenInstanceError):
        level.__setattr__("ratio", Decimal("2.618"))


@pytest.mark.parametrize(
    ("ratio", "message"),
    [
        (Decimal("0"), "ratio must be greater than 0"),
        (Decimal("-0.1"), "ratio must be greater than 0"),
        (Decimal("NaN"), "ratio must be finite"),
    ],
)
def test_fibonacci_level_rejects_invalid_ratio(ratio: Decimal, message: str) -> None:
    with pytest.raises(DomainError, match=message):
        FibonacciLevel(ratio=ratio)
