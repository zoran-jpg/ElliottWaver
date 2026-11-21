from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from tests.unit.application.forecast.test_forecast_engine import make_analysis_response
from tests.unit.domain.context.helpers import make_selected_wave_candidate

from elliottwaver.application.analysis import (
    AnalysisMetadata,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStage,
    AnalyzeMultiTimeframeUseCase,
    TimeframeAnalysisRequest,
)
from elliottwaver.application.analysis_application import AnalysisApplication
from elliottwaver.application.forecast import ForecastEngine
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId

if TYPE_CHECKING:
    from elliottwaver.domain.forecast import ForecastResult

_SYMBOL = Symbol("EURUSD")
_START = datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
_END = datetime(2026, 7, 21, 6, 0, tzinfo=UTC)
_ANALYSIS_ID = EntityId.parse("12345678-1234-5678-1234-567899999992")


def make_request() -> AnalysisRequest:
    timeframe_request = TimeframeAnalysisRequest(
        symbol=_SYMBOL,
        timeframe=MarketTimeframe.ONE_DAY,
        start_time=_START,
        end_time=_END,
    )
    return AnalysisRequest(
        symbol=_SYMBOL,
        timeframe_requests=(timeframe_request,),
        start_time=_START,
        end_time=_END,
    )


@dataclass(frozen=True, slots=True)
class StaticUseCase(AnalyzeMultiTimeframeUseCase):
    response: AnalysisResponse

    def analyze(self, _request: AnalysisRequest) -> AnalysisResponse:
        return self.response


def make_empty_completed_response() -> AnalysisResponse:
    metadata = AnalysisMetadata(
        analysis_id=_ANALYSIS_ID,
        correlation_id="corr-app",
        requested_at=_START,
        completed_at=_START,
        symbol=_SYMBOL,
        requested_timeframes=(),
        processed_timeframes=(),
    )
    return AnalysisResponse(metadata=metadata, stage=AnalysisStage.COMPLETED, timeframe_results=())


def test_analysis_application_runs_analysis_and_forecast() -> None:
    response = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )
    use_case = StaticUseCase(response=response)
    app = AnalysisApplication(analyze_use_case=use_case, forecast_engine=ForecastEngine())

    result = app.run(make_request())

    assert result.analysis is response
    assert result.forecast.primary_scenario is not None
    assert len(result.forecast.projections) == 2


def test_analysis_application_preserves_empty_projection_tuple() -> None:
    response = make_empty_completed_response()
    use_case = StaticUseCase(response=response)
    app = AnalysisApplication(analyze_use_case=use_case, forecast_engine=ForecastEngine())

    result = app.run(make_request())

    assert result.forecast.projections == ()


def test_analysis_application_propagates_domain_error_from_forecast() -> None:
    response = make_analysis_response(
        selected_wave=make_selected_wave_candidate(direction="down", score_percent="90"),
        confluence_percent="80",
    )

    @dataclass(frozen=True, slots=True)
    class FailingForecastEngine:
        def generate(self, _analysis: AnalysisResponse) -> ForecastResult:
            message = "projected price must be greater than 0"
            raise DomainError(message)

    use_case = StaticUseCase(response=response)
    app = AnalysisApplication(analyze_use_case=use_case, forecast_engine=FailingForecastEngine())

    with pytest.raises(DomainError, match="projected price must be greater than 0"):
        app.run(make_request())


def test_analysis_application_is_deterministic_for_repeated_calls() -> None:
    response = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )
    use_case = StaticUseCase(response=response)
    app = AnalysisApplication(analyze_use_case=use_case, forecast_engine=ForecastEngine())

    first = app.run(make_request())
    second = app.run(make_request())

    assert first == second


def test_analysis_application_keeps_projection_order() -> None:
    response = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )
    use_case = StaticUseCase(response=response)
    app = AnalysisApplication(analyze_use_case=use_case, forecast_engine=ForecastEngine())

    result = app.run(make_request())

    assert tuple(projection.level.ratio for projection in result.forecast.projections) == (
        Decimal("1.0"),
        Decimal("1.618"),
    )


def test_analysis_application_passes_through_projection_tuple_identity() -> None:
    response = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )
    forecast_result = ForecastEngine().generate(response)

    @dataclass(frozen=True, slots=True)
    class StaticForecastEngine:
        result: ForecastResult

        def generate(self, _analysis: AnalysisResponse) -> ForecastResult:
            return self.result

    use_case = StaticUseCase(response=response)
    app = AnalysisApplication(
        analyze_use_case=use_case,
        forecast_engine=StaticForecastEngine(result=forecast_result),
    )

    result = app.run(make_request()).forecast

    assert result.projections is forecast_result.projections
