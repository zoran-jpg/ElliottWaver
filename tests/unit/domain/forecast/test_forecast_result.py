from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from tests.unit.domain.forecast.helpers import make_forecast_scenario

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.forecast import (
    ForecastResult,
    ProjectionQuality,
    ScenarioType,
)
from elliottwaver.domain.market import Price
from elliottwaver.domain.projection import (
    FibonacciLevel,
    FibonacciProjection,
    ProjectionDirection,
)


def test_forecast_result_empty_forecast() -> None:
    result = ForecastResult(
        primary_scenario=None,
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.LOW,
        overall_confidence=Decimal("0"),
    )

    assert result.has_forecast is False
    assert result.scenario_count == 0
    assert result.projections == ()
    assert result.invalidated_scenarios == ()
    assert result.valid_alternative_scenarios == ()


def test_forecast_result_valid_primary_only() -> None:
    primary = make_forecast_scenario(scenario_type=ScenarioType.PRIMARY)
    result = ForecastResult(
        primary_scenario=primary,
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.HIGH,
        overall_confidence=Decimal("82"),
    )

    assert result.has_forecast is True
    assert result.scenario_count == 1


def test_forecast_result_accepts_projections() -> None:
    projection = FibonacciProjection(
        level=FibonacciLevel(ratio=Decimal("1.0")),
        price=Price.parse("120"),
        direction=ProjectionDirection.UP,
        reference_range=Decimal("20"),
    )

    result = ForecastResult(
        primary_scenario=make_forecast_scenario(scenario_type=ScenarioType.PRIMARY),
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.HIGH,
        overall_confidence=Decimal("82"),
        projections=(projection,),
    )

    assert result.projections == (projection,)


def test_forecast_result_primary_and_alternatives() -> None:
    primary = make_forecast_scenario(scenario_type=ScenarioType.PRIMARY)
    alternative = make_forecast_scenario(
        scenario_type=ScenarioType.ALTERNATIVE,
        confidence="65",
    )
    invalidated = make_forecast_scenario(
        scenario_type=ScenarioType.INVALIDATED,
        confidence="15",
        targets=(),
        reasoning=("Stopped out by invalidation",),
    )

    result = ForecastResult(
        primary_scenario=primary,
        alternative_scenarios=(alternative, invalidated),
        projection_quality=ProjectionQuality.MEDIUM,
        overall_confidence=Decimal("60"),
    )

    assert result.scenario_count == 3
    assert result.invalidated_scenarios == (invalidated,)
    assert result.valid_alternative_scenarios == (alternative,)


def test_forecast_result_rejects_duplicate_alternatives() -> None:
    alternative = make_forecast_scenario(scenario_type=ScenarioType.ALTERNATIVE)

    with pytest.raises(DomainError, match="must not contain duplicate instances"):
        ForecastResult(
            primary_scenario=make_forecast_scenario(scenario_type=ScenarioType.PRIMARY),
            alternative_scenarios=(alternative, alternative),
            projection_quality=ProjectionQuality.HIGH,
            overall_confidence=Decimal("70"),
        )


def test_forecast_result_rejects_invalid_primary_type() -> None:
    not_primary = make_forecast_scenario(scenario_type=ScenarioType.ALTERNATIVE)

    with pytest.raises(DomainError, match="primary_scenario must have scenario type PRIMARY"):
        ForecastResult(
            primary_scenario=not_primary,
            alternative_scenarios=(),
            projection_quality=ProjectionQuality.MEDIUM,
            overall_confidence=Decimal("50"),
        )


def test_forecast_result_rejects_invalid_confidence() -> None:
    with pytest.raises(DomainError, match=r"overall_confidence must be within \[0, 100\]"):
        ForecastResult(
            primary_scenario=make_forecast_scenario(scenario_type=ScenarioType.PRIMARY),
            alternative_scenarios=(),
            projection_quality=ProjectionQuality.HIGH,
            overall_confidence=Decimal("101"),
        )


def test_forecast_result_rejects_empty_forecast_with_non_zero_confidence() -> None:
    with pytest.raises(DomainError, match="empty forecasts must have zero overall confidence"):
        ForecastResult(
            primary_scenario=None,
            alternative_scenarios=(),
            projection_quality=ProjectionQuality.LOW,
            overall_confidence=Decimal("1"),
        )


def test_forecast_result_rejects_empty_forecast_with_non_low_quality() -> None:
    with pytest.raises(DomainError, match="empty forecasts must have LOW projection quality"):
        ForecastResult(
            primary_scenario=None,
            alternative_scenarios=(),
            projection_quality=ProjectionQuality.HIGH,
            overall_confidence=Decimal("0"),
        )


def test_forecast_result_default_projections_is_immutable_empty_tuple() -> None:
    result = ForecastResult(
        primary_scenario=make_forecast_scenario(scenario_type=ScenarioType.PRIMARY),
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.HIGH,
        overall_confidence=Decimal("82"),
    )

    assert result.projections == ()
    with pytest.raises(AttributeError):
        result.projections.append("x")  # type: ignore[attr-defined]


def test_forecast_result_instances_do_not_share_mutable_projection_state() -> None:
    first = ForecastResult(
        primary_scenario=make_forecast_scenario(scenario_type=ScenarioType.PRIMARY),
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.HIGH,
        overall_confidence=Decimal("82"),
    )
    second = ForecastResult(
        primary_scenario=make_forecast_scenario(scenario_type=ScenarioType.PRIMARY),
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.HIGH,
        overall_confidence=Decimal("82"),
    )

    assert first.projections is second.projections
    with pytest.raises(FrozenInstanceError):
        first.__setattr__("projections", ())


def test_forecast_result_preserves_projection_content_and_order() -> None:
    first_projection = FibonacciProjection(
        level=FibonacciLevel(ratio=Decimal("1.0")),
        price=Price.parse("120"),
        direction=ProjectionDirection.UP,
        reference_range=Decimal("20"),
    )
    second_projection = FibonacciProjection(
        level=FibonacciLevel(ratio=Decimal("1.618")),
        price=Price.parse("132.36"),
        direction=ProjectionDirection.UP,
        reference_range=Decimal("20"),
    )

    result = ForecastResult(
        primary_scenario=make_forecast_scenario(scenario_type=ScenarioType.PRIMARY),
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.HIGH,
        overall_confidence=Decimal("82"),
        projections=(first_projection, second_projection),
    )

    assert result.projections == (first_projection, second_projection)
