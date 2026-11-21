"""Forecast and projection domain components."""

from elliottwaver.domain.forecast.forecast_result import ForecastResult
from elliottwaver.domain.forecast.forecast_scenario import ForecastScenario
from elliottwaver.domain.forecast.projection_quality import ProjectionQuality
from elliottwaver.domain.forecast.projection_target import ProjectionTarget
from elliottwaver.domain.forecast.scenario_type import ScenarioType

__all__ = [
    "ForecastResult",
    "ForecastScenario",
    "ProjectionQuality",
    "ProjectionTarget",
    "ScenarioType",
]
