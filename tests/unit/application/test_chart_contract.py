from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from tests.unit.application.forecast.test_forecast_engine import (
    make_analysis_response,
    make_timeframe_result,
)
from tests.unit.domain.context.helpers import make_selected_wave_candidate

from elliottwaver.application import AnalysisApplicationResult
from elliottwaver.application.analysis import AnalysisMetadata, AnalysisResponse, AnalysisStage
from elliottwaver.application.chart_contract import build_chart_data_contract
from elliottwaver.application.forecast import ForecastEngine
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.forecast import ForecastResult, ProjectionQuality
from elliottwaver.domain.market import Candle, Pivot, PivotType, Price, Swing
from elliottwaver.domain.market.wave import Wave, WaveType


def _build_chart_ready_result() -> AnalysisApplicationResult:
    selected_wave = make_selected_wave_candidate(score_percent="91")
    timeframe_result = make_timeframe_result(
        timeframe=MarketTimeframe.ONE_HOUR,
        selected_wave=selected_wave,
    )

    symbol = Symbol("EURUSD")
    timeframe = MarketTimeframe.ONE_HOUR
    candle_1 = Candle(
        symbol=symbol,
        timeframe=timeframe,
        opened_at=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        open=Price.parse("100"),
        high=Price.parse("111"),
        low=Price.parse("99"),
        close=Price.parse("109"),
        volume=Decimal("10"),
    )
    candle_2 = Candle(
        symbol=symbol,
        timeframe=timeframe,
        opened_at=datetime(2026, 7, 20, 1, 0, tzinfo=UTC),
        open=Price.parse("109"),
        high=Price.parse("114"),
        low=Price.parse("106"),
        close=Price.parse("108"),
        volume=Decimal("12"),
    )

    pivot_low = Pivot(
        id=EntityId.parse("12345678-1234-5678-1234-567899999901"),
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        price=Price.parse("99"),
        pivot_type=PivotType.LOW,
    )
    pivot_high = Pivot(
        id=EntityId.parse("12345678-1234-5678-1234-567899999902"),
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2026, 7, 20, 1, 0, tzinfo=UTC),
        price=Price.parse("114"),
        pivot_type=PivotType.HIGH,
    )
    pivot_low_2 = Pivot(
        id=EntityId.parse("12345678-1234-5678-1234-567899999903"),
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2026, 7, 20, 2, 0, tzinfo=UTC),
        price=Price.parse("104"),
        pivot_type=PivotType.LOW,
    )

    swing_up = Swing(
        id=EntityId.parse("12345678-1234-5678-1234-567899999911"),
        start_pivot=pivot_low,
        end_pivot=pivot_high,
    )
    swing_down = Swing(
        id=EntityId.parse("12345678-1234-5678-1234-567899999912"),
        start_pivot=pivot_high,
        end_pivot=pivot_low_2,
    )

    timeframe_result = replace(
        timeframe_result,
        candles=(candle_2, candle_1),
        prepared_swings=(swing_down, swing_up),
    )

    metadata = AnalysisMetadata(
        analysis_id=EntityId.parse("12345678-1234-5678-1234-567899999921"),
        correlation_id="corr-chart",
        requested_at=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 20, 0, 5, tzinfo=UTC),
        symbol=symbol,
        requested_timeframes=(timeframe,),
        processed_timeframes=(timeframe,),
    )
    analysis = AnalysisResponse(
        metadata=metadata,
        stage=AnalysisStage.COMPLETED,
        timeframe_results=(timeframe_result,),
        multi_timeframe_analysis=None,
        trend_hierarchy=None,
        confluence_result=None,
        issues=(),
    )
    forecast = ForecastEngine().generate(analysis)
    return AnalysisApplicationResult(analysis=analysis, forecast=forecast)


def test_build_chart_data_contract_maps_and_orders_data_deterministically() -> None:
    result = _build_chart_ready_result()

    contract = build_chart_data_contract(result)

    assert contract.symbol == "EURUSD"
    assert len(contract.timeframe_data) == 1

    timeframe_data = contract.timeframe_data[0]
    assert timeframe_data.timeframe == "1h"

    assert [candle.opened_at for candle in timeframe_data.candles] == [
        datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 20, 1, 0, tzinfo=UTC),
    ]
    assert timeframe_data.candles[0].open_price == Decimal("100")
    assert timeframe_data.candles[0].high_price == Decimal("111")
    assert timeframe_data.candles[0].low_price == Decimal("99")
    assert timeframe_data.candles[0].close_price == Decimal("109")

    assert [swing.start_timestamp for swing in timeframe_data.swings] == [
        datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 20, 1, 0, tzinfo=UTC),
    ]
    assert [swing.end_timestamp for swing in timeframe_data.swings] == [
        datetime(2026, 7, 20, 1, 0, tzinfo=UTC),
        datetime(2026, 7, 20, 2, 0, tzinfo=UTC),
    ]
    assert [swing.direction for swing in timeframe_data.swings] == ["up", "down"]

    assert timeframe_data.swings[0].start_pivot_id == "12345678-1234-5678-1234-567899999901"
    assert timeframe_data.swings[0].end_pivot_id == "12345678-1234-5678-1234-567899999902"
    assert timeframe_data.swings[1].start_pivot_id == "12345678-1234-5678-1234-567899999902"
    assert timeframe_data.swings[1].end_pivot_id == "12345678-1234-5678-1234-567899999903"

    assert [pivot.timestamp for pivot in timeframe_data.pivots] == [
        datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 20, 1, 0, tzinfo=UTC),
        datetime(2026, 7, 20, 2, 0, tzinfo=UTC),
    ]
    assert [pivot.pivot_type for pivot in timeframe_data.pivots] == ["low", "high", "low"]
    assert [zone.zone_type for zone in timeframe_data.support_resistance_zones] == [
        "support",
        "resistance",
    ]
    support_zone = timeframe_data.support_resistance_zones[0]
    resistance_zone = timeframe_data.support_resistance_zones[1]
    assert support_zone.lower_price == Decimal("99")
    assert support_zone.upper_price == Decimal("100")
    assert resistance_zone.lower_price == Decimal("109")
    assert resistance_zone.upper_price == Decimal("114")

    assert len(contract.forecast_scenarios) >= 1
    assert contract.forecast_scenarios[0].scenario_type == "primary"
    assert len(contract.fibonacci_projections) >= 1


def test_build_chart_data_contract_maps_fibonacci_fields_and_enforces_order() -> None:
    result = _build_chart_ready_result()
    reversed_forecast = replace(
        result.forecast,
        projections=tuple(reversed(result.forecast.projections)),
    )

    contract = build_chart_data_contract(
        AnalysisApplicationResult(
            analysis=result.analysis,
            forecast=reversed_forecast,
        )
    )
    expected_sorted = tuple(
        sorted(
            result.forecast.projections,
            key=lambda projection: (
                projection.level.ratio,
                projection.direction.value,
                projection.price.value,
            ),
        )
    )

    assert [projection.level_ratio for projection in contract.fibonacci_projections] == sorted(
        projection.level.ratio for projection in result.forecast.projections
    )
    assert [projection.price for projection in contract.fibonacci_projections] == [
        projection.price.value for projection in expected_sorted
    ]
    assert [projection.direction for projection in contract.fibonacci_projections] == [
        projection.direction.value for projection in expected_sorted
    ]
    assert [projection.reference_range for projection in contract.fibonacci_projections] == [
        projection.reference_range for projection in expected_sorted
    ]


def test_build_chart_data_contract_maps_selected_wave_anchors_and_labels() -> None:
    result = _build_chart_ready_result()

    contract = build_chart_data_contract(result)

    selected_waves = contract.timeframe_data[0].selected_waves
    assert len(selected_waves) == 1

    selected_wave = selected_waves[0]
    assert selected_wave.wave_type == "impulse"
    assert selected_wave.wave_degree == "primary"
    assert selected_wave.selection_rank == 1
    assert len(selected_wave.anchors) == 6
    assert [anchor.label for anchor in selected_wave.anchors] == [None, "1", "2", "3", "4", "5"]


def test_build_chart_data_contract_hides_ambiguous_wave_labels() -> None:
    result = _build_chart_ready_result()
    selected_wave = make_selected_wave_candidate(score_percent="91")
    original_wave = selected_wave.wave_candidate.wave
    ambiguous_wave = Wave(
        id=original_wave.id,
        wave_type=WaveType.IMPULSE,
        degree=original_wave.degree,
        swings=original_wave.swings[:4],
    )
    selected_wave = replace(
        selected_wave,
        scored_candidate=replace(
            selected_wave.scored_candidate,
            candidate=replace(selected_wave.scored_candidate.candidate, wave=ambiguous_wave),
        ),
    )

    timeframe_result = replace(
        result.analysis.timeframe_results[0],
        selection_result=replace(
            result.analysis.timeframe_results[0].selection_result,
            selected_candidates=(selected_wave,),
        ),
    )
    analysis = replace(
        result.analysis,
        timeframe_results=(timeframe_result,),
    )

    contract = build_chart_data_contract(
        AnalysisApplicationResult(
            analysis=analysis,
            forecast=result.forecast,
        )
    )

    mapped_wave = contract.timeframe_data[0].selected_waves[0]
    assert [anchor.label for anchor in mapped_wave.anchors] == [None, None, None, None, None]


def test_build_chart_data_contract_rejects_missing_candle_data() -> None:
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="88"),
        confluence_percent="70",
    )
    forecast = ForecastEngine().generate(analysis)
    result = AnalysisApplicationResult(analysis=analysis, forecast=forecast)

    with pytest.raises(DomainError, match="at least one timeframe with candle data"):
        build_chart_data_contract(result)


def test_build_chart_data_contract_rejects_empty_timeframe_results() -> None:
    symbol = Symbol("EURUSD")
    metadata = AnalysisMetadata(
        analysis_id=EntityId.parse("12345678-1234-5678-1234-567899999931"),
        correlation_id="corr-empty",
        requested_at=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 20, 0, 1, tzinfo=UTC),
        symbol=symbol,
        requested_timeframes=(),
        processed_timeframes=(),
    )
    analysis = AnalysisResponse(
        metadata=metadata,
        stage=AnalysisStage.MARKET_DATA,
        timeframe_results=(),
        multi_timeframe_analysis=None,
        trend_hierarchy=None,
        confluence_result=None,
        issues=(),
    )
    forecast = ForecastResult(
        primary_scenario=None,
        alternative_scenarios=(),
        projection_quality=ProjectionQuality.LOW,
        overall_confidence=Decimal("0"),
        projections=(),
    )

    with pytest.raises(DomainError, match="at least one timeframe result"):
        build_chart_data_contract(AnalysisApplicationResult(analysis=analysis, forecast=forecast))


def test_build_chart_data_contract_rejects_conflicting_pivot_coordinates() -> None:
    result = _build_chart_ready_result()
    timeframe_result = result.analysis.timeframe_results[0]

    symbol = Symbol("EURUSD")
    timeframe = MarketTimeframe.ONE_HOUR
    shared_id = EntityId.parse("12345678-1234-5678-1234-567899999941")
    pivot_start = Pivot(
        id=EntityId.parse("12345678-1234-5678-1234-567899999942"),
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        price=Price.parse("100"),
        pivot_type=PivotType.LOW,
    )
    pivot_shared_a = Pivot(
        id=shared_id,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2026, 7, 20, 1, 0, tzinfo=UTC),
        price=Price.parse("110"),
        pivot_type=PivotType.HIGH,
    )
    pivot_shared_b = Pivot(
        id=shared_id,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2026, 7, 20, 2, 0, tzinfo=UTC),
        price=Price.parse("111"),
        pivot_type=PivotType.HIGH,
    )
    pivot_end = Pivot(
        id=EntityId.parse("12345678-1234-5678-1234-567899999943"),
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2026, 7, 20, 3, 0, tzinfo=UTC),
        price=Price.parse("105"),
        pivot_type=PivotType.LOW,
    )
    swing_a = Swing(
        id=EntityId.parse("12345678-1234-5678-1234-567899999951"),
        start_pivot=pivot_start,
        end_pivot=pivot_shared_a,
    )
    swing_b = Swing(
        id=EntityId.parse("12345678-1234-5678-1234-567899999952"),
        start_pivot=pivot_shared_b,
        end_pivot=pivot_end,
    )

    conflicting_timeframe_result = replace(
        timeframe_result,
        prepared_swings=(swing_a, swing_b),
    )
    conflicting_analysis = replace(
        result.analysis,
        timeframe_results=(conflicting_timeframe_result,),
    )

    with pytest.raises(DomainError, match="conflicting chart coordinates"):
        build_chart_data_contract(
            AnalysisApplicationResult(analysis=conflicting_analysis, forecast=result.forecast)
        )
