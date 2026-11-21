from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.domain.forecast import (
    ForecastScenario,
    ProjectionTarget,
    ScenarioType,
)
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.wave import WaveDegree

_SYMBOL = Symbol("EURUSD")


def make_projection_target(
    *,
    priority: int = 1,
    confidence: str = "70",
    description: str | None = "Primary extension",
) -> ProjectionTarget:
    return ProjectionTarget(
        target_price=Price.parse("123.45"),
        wave_degree=WaveDegree.PRIMARY,
        priority=priority,
        confidence=Decimal(confidence),
        description=description,
    )


def make_forecast_scenario(
    *,
    scenario_type: ScenarioType = ScenarioType.PRIMARY,
    confidence: str = "75",
    targets: tuple[ProjectionTarget, ...] | None = None,
    reasoning: tuple[str, ...] = ("Wave structure remains valid",),
) -> ForecastScenario:
    scenario_targets = targets
    if scenario_targets is None:
        scenario_targets = (make_projection_target(priority=1),)

    return ForecastScenario(
        scenario_type=scenario_type,
        expected_next_wave="Wave 5",
        confidence=Decimal(confidence),
        projection_targets=scenario_targets,
        reasoning=reasoning,
    )


def make_datetime() -> datetime:
    return datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


def make_symbol() -> Symbol:
    return _SYMBOL


def make_market_timeframe() -> MarketTimeframe:
    return MarketTimeframe.ONE_HOUR
