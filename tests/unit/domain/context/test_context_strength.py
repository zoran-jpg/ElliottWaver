from elliottwaver.domain.context import ContextStrength


def test_context_strength_values_are_stable() -> None:
    assert ContextStrength.WEAK.value == "weak"
    assert ContextStrength.MODERATE.value == "moderate"
    assert ContextStrength.STRONG.value == "strong"
    assert ContextStrength.VERY_STRONG.value == "very_strong"
