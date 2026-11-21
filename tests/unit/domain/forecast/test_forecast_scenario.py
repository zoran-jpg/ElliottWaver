from decimal import Decimal

import pytest
from tests.unit.domain.forecast.helpers import make_forecast_scenario, make_projection_target

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.forecast import ForecastScenario, ScenarioType


def test_forecast_scenario_valid_primary_alternative_and_invalidated() -> None:
    primary = make_forecast_scenario(scenario_type=ScenarioType.PRIMARY)
    alternative = make_forecast_scenario(scenario_type=ScenarioType.ALTERNATIVE)
    invalidated = ForecastScenario(
        scenario_type=ScenarioType.INVALIDATED,
        expected_next_wave="Wave 5 invalidated",
        confidence=Decimal("10"),
        projection_targets=(),
        reasoning=("Invalidation level was breached",),
    )

    assert primary.is_primary is True
    assert primary.is_alternative is False
    assert primary.is_invalidated is False

    assert alternative.is_primary is False
    assert alternative.is_alternative is True
    assert alternative.is_invalidated is False

    assert invalidated.is_primary is False
    assert invalidated.is_alternative is False
    assert invalidated.is_invalidated is True


def test_forecast_scenario_rejects_duplicate_priorities() -> None:
    duplicated = (
        make_projection_target(priority=1, confidence="65", description="target-a"),
        make_projection_target(priority=1, confidence="70", description="target-b"),
    )

    with pytest.raises(DomainError, match="priorities must be unique"):
        make_forecast_scenario(targets=duplicated)


def test_forecast_scenario_rejects_empty_targets_for_active_scenario() -> None:
    with pytest.raises(DomainError, match="active forecast scenarios must contain"):
        make_forecast_scenario(scenario_type=ScenarioType.PRIMARY, targets=())


def test_forecast_scenario_rejects_invalid_confidence() -> None:
    with pytest.raises(DomainError, match=r"confidence must be within \[0, 100\]"):
        make_forecast_scenario(confidence="-1")


def test_forecast_scenario_rejects_invalid_reasoning() -> None:
    with pytest.raises(DomainError, match="reasoning must not be empty"):
        make_forecast_scenario(reasoning=())

    with pytest.raises(DomainError, match="reasoning entries must not be empty"):
        make_forecast_scenario(reasoning=("valid", "   "))

    with pytest.raises(DomainError, match="reasoning entries must be unique"):
        make_forecast_scenario(reasoning=("duplicate", "duplicate"))


def test_forecast_scenario_rejects_non_consecutive_priorities() -> None:
    non_consecutive = (
        make_projection_target(priority=1),
        make_projection_target(priority=3, description="third"),
    )

    with pytest.raises(DomainError, match="priorities must be consecutive"):
        make_forecast_scenario(targets=non_consecutive)
