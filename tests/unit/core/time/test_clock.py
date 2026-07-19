from datetime import UTC

from elliottwaver.core.time.clock import utc_now


def test_utc_now_returns_utc_datetime() -> None:
    now = utc_now()

    assert now.tzinfo is UTC
