from __future__ import annotations

import importlib
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from tests.unit.domain.context.helpers import make_selected_wave_candidate

from elliottwaver.application.analysis import (
    AnalysisIssue,
    AnalysisIssueSeverity,
    AnalysisMetadata,
    AnalysisResponse,
    AnalysisStage,
    TimeframeAnalysisRequest,
    TimeframeAnalysisResult,
)
from elliottwaver.application.forecast import ForecastEngine
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.confluence import (
    ConfluenceConflict,
    ConfluenceSeverity,
    MultiTimeframeConfluenceResult,
)
from elliottwaver.domain.detection import DetectionResult
from elliottwaver.domain.forecast import ProjectionQuality, ScenarioType
from elliottwaver.domain.market import Price
from elliottwaver.domain.projection import (
    FibonacciLevel,
    FibonacciProjection,
    ProjectionDirection,
    ProjectionInput,
)
from elliottwaver.domain.scoring import ScoringResult
from elliottwaver.domain.selection import SelectedWaveCandidate, SelectionResult

_SYMBOL = Symbol("EURUSD")
_START = datetime(2026, 7, 20, 0, 0, tzinfo=UTC)
_END = datetime(2026, 7, 20, 6, 0, tzinfo=UTC)
_REQUESTED_AT = datetime(2026, 7, 20, 0, 0, tzinfo=UTC)
_COMPLETED_AT = datetime(2026, 7, 20, 0, 1, tzinfo=UTC)
_ANALYSIS_ID = EntityId.parse("12345678-1234-5678-1234-567899999991")


def make_timeframe_result(
    *,
    timeframe: MarketTimeframe,
    selected_wave: SelectedWaveCandidate | None,
) -> TimeframeAnalysisResult:
    request = TimeframeAnalysisRequest(
        symbol=_SYMBOL,
        timeframe=timeframe,
        start_time=_START,
        end_time=_END,
    )
    metadata = AnalysisMetadata(
        analysis_id=_ANALYSIS_ID,
        correlation_id="corr-forecast",
        requested_at=_REQUESTED_AT,
        completed_at=_COMPLETED_AT,
        symbol=_SYMBOL,
        requested_timeframes=(timeframe,),
        processed_timeframes=(timeframe,),
    )

    if selected_wave is None:
        detection_result = DetectionResult()
        scoring_result = ScoringResult()
        selection_result = SelectionResult(
            selected_candidates=(),
            policy_name="top_score",
            considered_candidates=0,
        )
        stage = AnalysisStage.SELECTION
    else:
        detection_result = DetectionResult(candidates=(selected_wave.wave_candidate,))
        scoring_result = ScoringResult(scored_candidates=(selected_wave.scored_candidate,))
        selection_result = SelectionResult(
            selected_candidates=(selected_wave,),
            policy_name="top_score",
            considered_candidates=1,
        )
        stage = AnalysisStage.COMPLETED

    return TimeframeAnalysisResult(
        request=request,
        metadata=metadata,
        candles=(),
        prepared_swings=(),
        detection_result=detection_result,
        scoring_result=scoring_result,
        selection_result=selection_result,
        issues=(),
        stage=stage,
    )


def make_confluence_result(
    *,
    percent: str,
    has_conflict: bool = False,
) -> MultiTimeframeConfluenceResult:
    conflicts: tuple[ConfluenceConflict, ...] = ()
    if has_conflict:
        conflicts = (
            ConfluenceConflict(
                rule_name="rule",
                conflict_code="code",
                message="conflict",
                severity=ConfluenceSeverity.WARNING,
            ),
        )

    value = Decimal(percent)
    return MultiTimeframeConfluenceResult(
        relation_results=(),
        analyzed_relations_count=0,
        confluence_score=value,
        maximum_confluence_score=Decimal("100"),
        confluence_percent=value,
        evidences=(),
        conflicts=conflicts,
        hierarchy_validation_result=None,
    )


def make_analysis_response(
    *,
    selected_wave: SelectedWaveCandidate | None,
    confluence_percent: str | None = None,
    has_conflict: bool = False,
    issues: tuple[AnalysisIssue, ...] = (),
    stage: AnalysisStage = AnalysisStage.COMPLETED,
) -> AnalysisResponse:
    timeframe_result = make_timeframe_result(
        timeframe=MarketTimeframe.ONE_DAY,
        selected_wave=selected_wave,
    )
    metadata = AnalysisMetadata(
        analysis_id=_ANALYSIS_ID,
        correlation_id="corr-forecast",
        requested_at=_REQUESTED_AT,
        completed_at=_COMPLETED_AT,
        symbol=_SYMBOL,
        requested_timeframes=(MarketTimeframe.ONE_DAY,),
        processed_timeframes=(MarketTimeframe.ONE_DAY,),
    )

    confluence_result = None
    if confluence_percent is not None:
        confluence_result = make_confluence_result(
            percent=confluence_percent,
            has_conflict=has_conflict,
        )

    return AnalysisResponse(
        metadata=metadata,
        stage=stage,
        timeframe_results=(timeframe_result,),
        multi_timeframe_analysis=None,
        trend_hierarchy=None,
        confluence_result=confluence_result,
        issues=issues,
    )


def test_generate_primary_only_normal_forecast() -> None:
    engine = ForecastEngine()
    selected = make_selected_wave_candidate(score_percent="90")
    analysis = make_analysis_response(
        selected_wave=selected,
        confluence_percent="80",
    )

    result = engine.generate(analysis)

    assert result.primary_scenario is not None
    assert result.primary_scenario.scenario_type is ScenarioType.PRIMARY
    assert result.alternative_scenarios == ()
    assert len(result.projections) == 2
    assert result.overall_confidence == Decimal("87.0")
    assert result.projection_quality is ProjectionQuality.VERY_HIGH


def test_generate_primary_and_alternative_when_issues_present() -> None:
    engine = ForecastEngine()
    selected = make_selected_wave_candidate(score_percent="90")
    issue = AnalysisIssue(
        stage=AnalysisStage.CONFLUENCE,
        issue_code="confluence_conflict",
        message="Conflict detected",
        severity=AnalysisIssueSeverity.WARNING,
    )
    analysis = make_analysis_response(
        selected_wave=selected,
        confluence_percent="80",
        issues=(issue,),
    )

    result = engine.generate(analysis)

    assert result.primary_scenario is not None
    assert len(result.alternative_scenarios) == 1
    assert result.alternative_scenarios[0].scenario_type is ScenarioType.ALTERNATIVE
    assert result.overall_confidence == Decimal("72.0")
    assert result.projection_quality is ProjectionQuality.HIGH


def test_generate_primary_and_alternative_when_confluence_conflicts_exist() -> None:
    engine = ForecastEngine()
    selected = make_selected_wave_candidate(score_percent="90")
    analysis = make_analysis_response(
        selected_wave=selected,
        confluence_percent="80",
        has_conflict=True,
    )

    result = engine.generate(analysis)

    assert len(result.alternative_scenarios) == 1
    assert any(
        "Confluence conflicts detected" in reason
        for reason in result.alternative_scenarios[0].reasoning
    )


def test_generate_projection_targets_are_created_deterministically() -> None:
    engine = ForecastEngine()
    selected = make_selected_wave_candidate(score_percent="95")
    analysis = make_analysis_response(
        selected_wave=selected,
        confluence_percent="90",
    )

    result = engine.generate(analysis)

    primary = result.primary_scenario
    assert primary is not None
    assert len(primary.projection_targets) == 2
    assert primary.projection_targets[0].priority == 1
    assert primary.projection_targets[1].priority == 2
    assert primary.projection_targets[0].target_price.value == Decimal("159")
    assert primary.projection_targets[1].target_price.value == Decimal("178")


def test_generate_reasoning_contains_human_readable_entries() -> None:
    engine = ForecastEngine()
    selected = make_selected_wave_candidate(score_percent="88")
    analysis = make_analysis_response(
        selected_wave=selected,
        confluence_percent="70",
    )

    result = engine.generate(analysis)

    primary = result.primary_scenario
    assert primary is not None
    assert len(primary.reasoning) >= 2
    assert any("Selected wave score" in entry for entry in primary.reasoning)


def test_generate_empty_forecast_when_no_selected_wave() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=None,
        confluence_percent="50",
    )

    result = engine.generate(analysis)

    assert result.primary_scenario is None
    assert result.has_forecast is False
    assert result.scenario_count == 0
    assert result.projections == ()
    assert result.projection_quality is ProjectionQuality.LOW
    assert result.overall_confidence == Decimal("0")


@pytest.mark.parametrize(
    "analysis",
    [
        None,
        make_analysis_response(
            selected_wave=make_selected_wave_candidate(),
            confluence_percent="80",
            stage=AnalysisStage.CONFLUENCE,
        ),
    ],
)
def test_generate_rejects_invalid_input(analysis: AnalysisResponse | None) -> None:
    engine = ForecastEngine()

    with pytest.raises(DomainError):
        engine.generate(analysis)


def test_generate_is_deterministic() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )

    first = engine.generate(analysis)
    second = engine.generate(analysis)

    assert first == second


def test_generate_creates_alternative_for_low_confidence_primary() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="40"),
        confluence_percent="0",
    )

    result = engine.generate(analysis)

    assert result.primary_scenario is not None
    assert len(result.alternative_scenarios) == 1
    assert result.primary_scenario.confidence < Decimal("65")


def test_generate_primary_reasoning_without_confluence_result() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="85"),
        confluence_percent=None,
    )

    result = engine.generate(analysis)

    primary = result.primary_scenario
    assert primary is not None
    assert any("No confluence result available" in reason for reason in primary.reasoning)


def test_clamp_percent_handles_invalid_and_bound_values() -> None:
    engine = ForecastEngine()

    with pytest.raises(DomainError, match="percent value must be finite"):
        engine._clamp_percent(Decimal("NaN"))

    assert engine._clamp_percent(Decimal("-1")) == Decimal("0")
    assert engine._clamp_percent(Decimal("101")) == Decimal("100")


def test_generate_includes_fibonacci_projections_for_up_direction() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(direction="up", score_percent="90"),
        confluence_percent="80",
    )

    result = engine.generate(analysis)

    assert tuple(projection.level.ratio for projection in result.projections) == (
        Decimal("1.0"),
        Decimal("1.618"),
    )
    assert tuple(projection.price.value for projection in result.projections) == (
        Decimal("159"),
        Decimal("170.742"),
    )


def test_generate_includes_fibonacci_projections_for_down_direction() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(direction="down", score_percent="90"),
        confluence_percent="80",
    )

    result = engine.generate(analysis)

    assert tuple(projection.level.ratio for projection in result.projections) == (
        Decimal("1.0"),
        Decimal("1.618"),
    )
    assert tuple(projection.price.value for projection in result.projections) == (
        Decimal("79"),
        Decimal("66.022"),
    )


def test_generate_projections_are_deterministic() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(direction="up", score_percent="90"),
        confluence_percent="80",
    )

    first = engine.generate(analysis)
    second = engine.generate(analysis)

    assert first.projections == second.projections


def test_generate_calls_projection_engine_once_with_expected_input() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(direction="up", score_percent="90"),
        confluence_percent="80",
    )

    forecast_engine_module = importlib.import_module(
        "elliottwaver.application.forecast.forecast_engine"
    )
    original_project = forecast_engine_module.FibonacciProjectionEngine.project
    calls: list[tuple[object, tuple[FibonacciLevel, ...]]] = []

    def spy_project(
        self: object,
        projection_input: object,
        levels: tuple[FibonacciLevel, ...],
    ) -> object:
        calls.append((projection_input, levels))
        return original_project(self, projection_input, levels)

    forecast_engine_module.FibonacciProjectionEngine.project = spy_project
    try:
        _ = engine.generate(analysis)
    finally:
        forecast_engine_module.FibonacciProjectionEngine.project = original_project

    assert len(calls) == 1
    projection_input_obj, levels = calls[0]
    assert isinstance(projection_input_obj, ProjectionInput)
    assert projection_input_obj.start_price.value == Decimal("121")
    assert projection_input_obj.end_price.value == Decimal("140")
    assert projection_input_obj.projection_origin.value == Decimal("140")
    assert projection_input_obj.direction is ProjectionDirection.UP
    assert tuple(level.ratio for level in levels) == (Decimal("1.0"), Decimal("1.618"))


def test_generate_passes_projection_results_through_unchanged() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(direction="up", score_percent="90"),
        confluence_percent="80",
    )

    duplicate_projection = FibonacciProjection(
        level=FibonacciLevel(ratio=Decimal("1.0")),
        price=Price.parse("111"),
        direction=ProjectionDirection.UP,
        reference_range=Decimal("10"),
    )
    returned_tuple = (duplicate_projection, duplicate_projection)

    forecast_engine_module = importlib.import_module(
        "elliottwaver.application.forecast.forecast_engine"
    )
    original_project = forecast_engine_module.FibonacciProjectionEngine.project

    def fake_project(
        _self: object,
        *,
        projection_input: object,
        levels: object,
    ) -> object:
        _ = (projection_input, levels)
        return returned_tuple

    forecast_engine_module.FibonacciProjectionEngine.project = fake_project
    try:
        result = engine.generate(analysis)
    finally:
        forecast_engine_module.FibonacciProjectionEngine.project = original_project

    assert result.projections is returned_tuple
    assert result.projections[0] is duplicate_projection
    assert result.projections[1] is duplicate_projection


def test_generate_propagates_domain_error_from_projection_engine() -> None:
    engine = ForecastEngine()
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(direction="up", score_percent="90"),
        confluence_percent="80",
    )

    forecast_engine_module = importlib.import_module(
        "elliottwaver.application.forecast.forecast_engine"
    )
    original_project = forecast_engine_module.FibonacciProjectionEngine.project

    def failing_project(
        _self: object,
        *,
        projection_input: object,
        levels: object,
    ) -> object:
        _ = (projection_input, levels)
        message = "projected price must be greater than 0"
        raise DomainError(message)

    forecast_engine_module.FibonacciProjectionEngine.project = failing_project
    try:
        with pytest.raises(DomainError, match="projected price must be greater than 0"):
            engine.generate(analysis)
    finally:
        forecast_engine_module.FibonacciProjectionEngine.project = original_project
