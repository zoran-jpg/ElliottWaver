"""Immutable result of the Elliott forecast engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.forecast.projection_quality import ProjectionQuality
from elliottwaver.domain.forecast.scenario_type import ScenarioType

if TYPE_CHECKING:
    from elliottwaver.domain.forecast.forecast_scenario import ForecastScenario
    from elliottwaver.domain.projection import FibonacciProjection


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class ForecastResult:
    """Complete deterministic forecast output."""

    primary_scenario: ForecastScenario | None
    alternative_scenarios: tuple[ForecastScenario, ...]
    projection_quality: ProjectionQuality
    overall_confidence: Decimal
    projections: tuple[FibonacciProjection, ...] = ()

    def __post_init__(self) -> None:
        """Validate forecast-result invariants."""

        _validate_percent(self.overall_confidence, "overall_confidence")
        _validate_primary_scenario(self.primary_scenario)
        _validate_alternative_scenarios(self.alternative_scenarios)
        _validate_empty_forecast(self)

    @property
    def has_forecast(self) -> bool:
        """Return whether a primary scenario is available."""

        return self.primary_scenario is not None

    @property
    def is_empty(self) -> bool:
        """Return whether the result contains no scenarios."""

        return self.primary_scenario is None and not self.alternative_scenarios

    @property
    def scenario_count(self) -> int:
        """Return the total number of contained scenarios."""

        return int(self.primary_scenario is not None) + len(self.alternative_scenarios)

    @property
    def invalidated_scenarios(self) -> tuple[ForecastScenario, ...]:
        """Return invalidated scenarios contained in the secondary collection."""

        return tuple(
            scenario
            for scenario in self.alternative_scenarios
            if scenario.scenario_type is ScenarioType.INVALIDATED
        )

    @property
    def valid_alternative_scenarios(self) -> tuple[ForecastScenario, ...]:
        """Return active alternative scenarios."""

        return tuple(
            scenario
            for scenario in self.alternative_scenarios
            if scenario.scenario_type is ScenarioType.ALTERNATIVE
        )


def _validate_primary_scenario(primary_scenario: ForecastScenario | None) -> None:
    if primary_scenario is not None and primary_scenario.scenario_type is not ScenarioType.PRIMARY:
        message = "primary_scenario must have scenario type PRIMARY"
        raise DomainError(message)


def _validate_alternative_scenarios(
    alternative_scenarios: tuple[ForecastScenario, ...],
) -> None:
    if any(scenario.scenario_type is ScenarioType.PRIMARY for scenario in alternative_scenarios):
        message = "alternative_scenarios must not contain PRIMARY scenarios"
        raise DomainError(message)

    scenario_ids = tuple(id(scenario) for scenario in alternative_scenarios)

    if len(set(scenario_ids)) != len(scenario_ids):
        message = "alternative_scenarios must not contain duplicate instances"
        raise DomainError(message)


def _validate_empty_forecast(forecast_result: ForecastResult) -> None:
    if not forecast_result.is_empty:
        return

    if forecast_result.overall_confidence != _ZERO:
        message = "empty forecasts must have zero overall confidence"
        raise DomainError(message)

    if forecast_result.projection_quality is not ProjectionQuality.LOW:
        message = "empty forecasts must have LOW projection quality"
        raise DomainError(message)


def _validate_percent(value: Decimal, field_name: str) -> None:
    if not value.is_finite():
        message = f"{field_name} must be finite"
        raise DomainError(message)

    if value < _ZERO or value > _HUNDRED:
        message = f"{field_name} must be within [0, 100]"
        raise DomainError(message)
