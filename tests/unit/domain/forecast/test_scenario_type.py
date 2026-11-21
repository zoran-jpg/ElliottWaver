from elliottwaver.domain.forecast import ScenarioType


def test_scenario_type_enum_members_and_string_values() -> None:
    assert ScenarioType.PRIMARY.value == "primary"
    assert ScenarioType.ALTERNATIVE.value == "alternative"
    assert ScenarioType.INVALIDATED.value == "invalidated"


def test_scenario_type_equality_and_uniqueness() -> None:
    parsed = ScenarioType("primary")
    alternative = next(member for member in ScenarioType if member.value == "alternative")

    assert parsed == ScenarioType.PRIMARY
    assert parsed != alternative
    assert len({member.value for member in ScenarioType}) == len(ScenarioType)
