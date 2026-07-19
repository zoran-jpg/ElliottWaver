from elliottwaver.domain.context import CompletionLevel


def test_completion_level_values_are_stable() -> None:
    assert CompletionLevel.EARLY.value == "early"
    assert CompletionLevel.DEVELOPING.value == "developing"
    assert CompletionLevel.MATURE.value == "mature"
    assert CompletionLevel.COMPLETED.value == "completed"
