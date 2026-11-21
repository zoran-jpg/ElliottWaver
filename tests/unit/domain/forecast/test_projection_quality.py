from elliottwaver.domain.forecast import ProjectionQuality


def test_projection_quality_enum_values() -> None:
    assert ProjectionQuality.LOW.value == "low"
    assert ProjectionQuality.MEDIUM.value == "medium"
    assert ProjectionQuality.HIGH.value == "high"
    assert ProjectionQuality.VERY_HIGH.value == "very_high"


def test_projection_quality_equality_and_uniqueness() -> None:
    parsed = ProjectionQuality("high")
    medium = next(member for member in ProjectionQuality if member.value == "medium")

    assert parsed == ProjectionQuality.HIGH
    assert parsed != medium
    assert len({member.value for member in ProjectionQuality}) == len(ProjectionQuality)


def test_projection_quality_ordering_if_implemented() -> None:
    assert ProjectionQuality.HIGH < ProjectionQuality.MEDIUM
    assert ProjectionQuality.LOW < ProjectionQuality.VERY_HIGH
