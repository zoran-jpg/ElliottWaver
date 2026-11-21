from elliottwaver.domain.projection import ProjectionDirection


def test_projection_direction_enum_values() -> None:
    assert ProjectionDirection.UP.value == "up"
    assert ProjectionDirection.DOWN.value == "down"


def test_projection_direction_uniqueness() -> None:
    assert len({member.value for member in ProjectionDirection}) == len(ProjectionDirection)
