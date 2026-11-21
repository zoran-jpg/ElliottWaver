from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Price
from elliottwaver.domain.projection import (
    FibonacciLevel,
    FibonacciProjectionEngine,
    ProjectionDirection,
    ProjectionInput,
)


def make_projection_input(
    *,
    start_price: str,
    end_price: str,
    projection_origin: str,
    direction: ProjectionDirection,
) -> ProjectionInput:
    return ProjectionInput(
        start_price=Price.parse(start_price),
        end_price=Price.parse(end_price),
        projection_origin=Price.parse(projection_origin),
        direction=direction,
    )


def test_project_up_single_level() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="115",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("0.5")),))

    assert len(result) == 1
    assert result[0].price.value == Decimal("125")


def test_project_up_multiple_levels() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="115",
        direction=ProjectionDirection.UP,
    )
    levels = (
        FibonacciLevel(Decimal("0.382")),
        FibonacciLevel(Decimal("1.0")),
        FibonacciLevel(Decimal("1.618")),
    )

    result = engine.project(projection_input, levels)

    assert tuple(item.level for item in result) == levels
    assert tuple(item.price.value for item in result) == (
        Decimal("122.640"),
        Decimal("135"),
        Decimal("147.360"),
    )


def test_project_down_single_level() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="80",
        end_price="100",
        projection_origin="95",
        direction=ProjectionDirection.DOWN,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("0.5")),))

    assert len(result) == 1
    assert result[0].price.value == Decimal("85")


def test_project_down_multiple_levels() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="80",
        end_price="100",
        projection_origin="95",
        direction=ProjectionDirection.DOWN,
    )
    levels = (
        FibonacciLevel(Decimal("0.382")),
        FibonacciLevel(Decimal("1.0")),
    )

    result = engine.project(projection_input, levels)

    assert tuple(item.price.value for item in result) == (
        Decimal("87.360"),
        Decimal("75"),
    )


def test_project_uses_absolute_reference_range_for_low_to_high_reference() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("1.0")),))

    assert result[0].reference_range == Decimal("20")


def test_project_uses_absolute_reference_range_for_high_to_low_reference() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="120",
        end_price="100",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("1.0")),))

    assert result[0].reference_range == Decimal("20")
    assert result[0].price.value == Decimal("130")


def test_project_preserves_level_order() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )
    first = FibonacciLevel(Decimal("1.618"))
    second = FibonacciLevel(Decimal("0.5"))

    result = engine.project(projection_input, (first, second))

    assert tuple(item.level for item in result) == (first, second)


def test_project_preserves_duplicate_levels() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )
    level = FibonacciLevel(Decimal("0.5"))

    result = engine.project(projection_input, (level, level))

    assert len(result) == 2
    assert result[0].level == result[1].level
    assert result[0].price.value == result[1].price.value


def test_project_returns_empty_immutable_tuple_for_empty_levels() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, ())

    assert result == ()
    with pytest.raises(AttributeError):
        result.append("x")  # type: ignore[attr-defined]


def test_project_result_collection_is_immutable() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )
    result = engine.project(projection_input, (FibonacciLevel(Decimal("1.0")),))

    assert isinstance(result, tuple)

    with pytest.raises(AttributeError):
        object.__getattribute__(result, "append")


def test_project_target_price_uses_exact_decimal_math_without_rounding() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="10.001",
        end_price="10.004",
        projection_origin="10.002",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("1.618")),))

    assert result[0].price.value == Decimal("10.006854")


def test_project_down_non_positive_target_fails_explicitly() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="10",
        direction=ProjectionDirection.DOWN,
    )

    with pytest.raises(DomainError, match="projected price must be greater than 0"):
        engine.project(projection_input, (FibonacciLevel(Decimal("0.5")),))


def test_project_down_negative_target_fails_explicitly() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="9",
        direction=ProjectionDirection.DOWN,
    )

    with pytest.raises(DomainError, match="projected price must be greater than 0"):
        engine.project(projection_input, (FibonacciLevel(Decimal("0.5")),))


def test_project_is_deterministic_for_repeated_calls() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )
    levels = (
        FibonacciLevel(Decimal("0.382")),
        FibonacciLevel(Decimal("1.0")),
    )

    first = engine.project(projection_input, levels)
    second = engine.project(projection_input, levels)

    assert first == second


def test_projection_engine_is_exported_from_package() -> None:
    assert FibonacciProjectionEngine.__name__ == "FibonacciProjectionEngine"


def test_projection_results_are_frozen_dataclasses() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("1.0")),))

    with pytest.raises(FrozenInstanceError):
        result[0].__setattr__("reference_range", Decimal("1"))


def test_project_accepts_iterable_levels() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="100",
        end_price="120",
        projection_origin="110",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(
        projection_input,
        [FibonacciLevel(Decimal("0.5")), FibonacciLevel(Decimal("1.0"))],
    )

    assert tuple(item.price.value for item in result) == (Decimal("120"), Decimal("130"))


def test_project_handles_very_small_reference_movement() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="1.0000001",
        end_price="1.0000003",
        projection_origin="1.0000002",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("0.0001")),))

    assert result[0].reference_range == Decimal("0.0000002")
    assert result[0].price.value == Decimal("1.00000020002")


def test_project_handles_very_large_reference_movement() -> None:
    engine = FibonacciProjectionEngine()
    projection_input = make_projection_input(
        start_price="1000",
        end_price="1000001000",
        projection_origin="500000000",
        direction=ProjectionDirection.UP,
    )

    result = engine.project(projection_input, (FibonacciLevel(Decimal("2.618")),))

    assert result[0].reference_range == Decimal("1000000000")
    assert result[0].price.value == Decimal("3118000000")
