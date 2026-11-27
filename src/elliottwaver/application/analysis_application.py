"""Application facade for a complete analysis and forecast run."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from elliottwaver.application.analysis import AnalysisStage
from elliottwaver.domain.forecast import ForecastResult, ProjectionQuality

if TYPE_CHECKING:
    from elliottwaver.application.analysis import (
        AnalysisRequest,
        AnalysisResponse,
        AnalyzeMultiTimeframeUseCase,
    )


@runtime_checkable
class ForecastUseCase(Protocol):
    """Application-level contract for deterministic forecast generation."""

    def generate(self, analysis: AnalysisResponse) -> ForecastResult:
        """Create a forecast from an analysis response."""


@dataclass(frozen=True, slots=True)
class AnalysisApplicationResult:
    """Immutable application result tailored for outer adapters."""

    analysis: AnalysisResponse
    forecast: ForecastResult


@dataclass(frozen=True, slots=True)
class AnalysisApplication:
    """Coordinate analysis and forecast services for one application use case."""

    analyze_use_case: AnalyzeMultiTimeframeUseCase
    forecast_engine: ForecastUseCase

    def run(self, request: AnalysisRequest) -> AnalysisApplicationResult:
        """Run the complete analysis and forecast workflow for one request."""

        analysis = self.analyze_use_case.analyze(request)
        forecast = self.forecast_engine.generate(analysis)
        return AnalysisApplicationResult(analysis=analysis, forecast=forecast)

    def run_with_optional_forecast(self, request: AnalysisRequest) -> AnalysisApplicationResult:
        """Run analysis once and generate forecast only when analysis is forecast-eligible."""

        analysis = self.analyze_use_case.analyze(request)
        if analysis.stage is not AnalysisStage.COMPLETED:
            return AnalysisApplicationResult(analysis=analysis, forecast=_empty_forecast_result())

        forecast = self.forecast_engine.generate(analysis)
        return AnalysisApplicationResult(analysis=analysis, forecast=forecast)


def _empty_forecast_result() -> ForecastResult:
    return ForecastResult(
        primary_scenario=None,
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.LOW,
        overall_confidence=Decimal("0"),
        projections=(),
    )
