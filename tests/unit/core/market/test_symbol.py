import pytest

from elliottwaver.core.market import Symbol


def test_symbol_normalizes_value() -> None:
    symbol = Symbol("  btc-usdt  ")

    assert symbol.value == "BTC-USDT"
    assert str(symbol) == "BTC-USDT"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "BTC/USDT",
        "$BTC",
        "A" * 33,
    ],
)
def test_symbol_rejects_invalid_value(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid market symbol"):
        Symbol(value)
