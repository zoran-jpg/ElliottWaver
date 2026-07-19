from elliottwaver.core.result import Failure, Success


def test_success() -> None:
    result = Success(42)

    assert result.value == 42


def test_failure() -> None:
    result = Failure("error")

    assert result.error == "error"
