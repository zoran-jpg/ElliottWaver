from decimal import Decimal

import pytest

from elliottwaver.domain.market import Price


def test_price_parse_creates_decimal_price() -> None:
    price = Price.parse("123.450")

    assert price.value == Decimal("123.450")
    assert str(price) == "123.450"


@pytest.mark.parametrize(
    "value",
    [
        "-1",
        "NaN",
        "Infinity",
        "invalid",
    ],
)
def test_price_rejects_invalid_value(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid market price"):
        Price.parse(value)


def test_price_supports_ordering() -> None:
    lower = Price.parse("10")
    higher = Price.parse("20")

    assert lower < higher
