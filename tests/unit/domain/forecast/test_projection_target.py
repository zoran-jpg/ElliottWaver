from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from tests.unit.domain.forecast.helpers import make_projection_target

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.forecast import ProjectionTarget
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.wave import WaveDegree


def test_projection_target_valid_construction_and_equality() -> None:
    first = ProjectionTarget(
        target_price=Price.parse("123.45"),
        wave_degree=WaveDegree.PRIMARY,
        priority=1,
        confidence=Decimal("80"),
        description="Primary extension",
    )
    second = make_projection_target(priority=1, confidence="80")

    assert first == second


def test_projection_target_rejects_invalid_confidence() -> None:
    with pytest.raises(DomainError, match=r"confidence must be within \[0, 100\]"):
        make_projection_target(confidence="101")

    with pytest.raises(DomainError, match="confidence must be finite"):
        make_projection_target(confidence="NaN")


def test_projection_target_rejects_invalid_priority() -> None:
    with pytest.raises(DomainError, match="priority must be >= 1"):
        make_projection_target(priority=0)


def test_projection_target_rejects_empty_description() -> None:
    with pytest.raises(DomainError, match="description must not be empty"):
        make_projection_target(description="   ")


def test_projection_target_is_frozen() -> None:
    target = make_projection_target()

    with pytest.raises(FrozenInstanceError):
        target.__setattr__("priority", 2)
