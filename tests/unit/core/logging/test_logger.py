from elliottwaver.core.logging.logger import get_logger


def test_get_logger_returns_logger() -> None:
    assert get_logger() is not None
