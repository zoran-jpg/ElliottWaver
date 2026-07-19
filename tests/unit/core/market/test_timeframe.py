import pytest

from elliottwaver.core.market import Timeframe


def test_timeframe_parse_normalizes_value() -> None:
    timeframe = Timeframe.parse(" 4H ")

    assert timeframe is Timeframe.FOUR_HOURS
    assert timeframe.value == "4h"


def test_timeframe_parse_rejects_unsupported_value() -> None:
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        Timeframe.parse("2h")
