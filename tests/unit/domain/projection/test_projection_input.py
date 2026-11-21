from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Price
from elliottwaver.domain.projection import ProjectionDirection, ProjectionInput


def test_projection_input_valid_construction_and_reference_range() -> None:
    projection_input = ProjectionInput(
        start_price=Price.parse("100"),
        end_price=Price.parse("120"),
        projection_origin=Price.parse("115"),
        direction=ProjectionDirection.UP,
    )

    assert projection_input.reference_range == Decimal("20")


def test_projection_input_is_frozen() -> None:
    projection_input = ProjectionInput(
        start_price=Price.parse("100"),
        end_price=Price.parse("120"),
        projection_origin=Price.parse("115"),
        direction=ProjectionDirection.DOWN,
    )

    with pytest.raises(FrozenInstanceError):
        projection_input.__setattr__("direction", ProjectionDirection.UP)


def test_projection_input_rejects_zero_reference_movement() -> None:
    with pytest.raises(DomainError, match="reference movement must not be zero"):
        ProjectionInput(
            start_price=Price.parse("100"),
            end_price=Price.parse("100"),
            projection_origin=Price.parse("100"),
            direction=ProjectionDirection.UP,
        )


def test_projection_input_rejects_non_finite_raw_start_price() -> None:
    raw_price = object.__new__(Price)
    object.__setattr__(raw_price, "value", Decimal("NaN"))

    with pytest.raises(
        DomainError,
        match="start_price must be a valid non-negative price",
    ):
        ProjectionInput(
            start_price=raw_price,
            end_price=Price.parse("120"),
            projection_origin=Price.parse("115"),
            direction=ProjectionDirection.UP,
        )


def test_projection_input_rejects_negative_raw_projection_origin() -> None:
    raw_price = object.__new__(Price)
    object.__setattr__(raw_price, "value", Decimal("-1"))

    with pytest.raises(
        DomainError,
        match="projection_origin must be a valid non-negative price",
    ):
        ProjectionInput(
            start_price=Price.parse("100"),
            end_price=Price.parse("120"),
            projection_origin=raw_price,
            direction=ProjectionDirection.UP,
        )
