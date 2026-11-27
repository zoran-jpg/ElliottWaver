"""UI-independent chart data contract and deterministic mapping helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from elliottwaver.application.support_resistance import derive_support_resistance_zones
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market.wave import WaveType

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from elliottwaver.application.analysis import TimeframeAnalysisResult
    from elliottwaver.application.analysis_application import AnalysisApplicationResult
    from elliottwaver.domain.market import Swing
    from elliottwaver.domain.market.wave import Wave
    from elliottwaver.domain.selection import SelectionResult


_IMPULSE_WAVE_COUNT = 5
_CORRECTIVE_WAVE_COUNT = 3


@dataclass(frozen=True, slots=True)
class ChartCandle:
    """Immutable OHLC candle payload for chart rendering."""

    opened_at: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal


@dataclass(frozen=True, slots=True)
class ChartPivot:
    """Immutable pivot payload with explicit timestamp and source identity."""

    pivot_id: str
    timestamp: datetime
    price: Decimal
    pivot_type: str


@dataclass(frozen=True, slots=True)
class ChartSwing:
    """Immutable swing payload with deterministic time/price anchors."""

    swing_id: str
    direction: str
    start_timestamp: datetime
    end_timestamp: datetime
    start_price: Decimal
    end_price: Decimal
    start_pivot_id: str
    end_pivot_id: str


@dataclass(frozen=True, slots=True)
class ChartWaveAnchor:
    """Immutable anchor point used to render selected Elliott waves."""

    pivot_id: str
    timestamp: datetime
    price: Decimal
    label: str | None


@dataclass(frozen=True, slots=True)
class ChartWave:
    """Immutable selected-wave payload for chart overlays."""

    wave_id: str
    wave_type: str
    wave_degree: str
    selection_rank: int
    anchors: tuple[ChartWaveAnchor, ...]


@dataclass(frozen=True, slots=True)
class ChartProjectionTarget:
    """Immutable projection target payload mapped from forecast scenarios."""

    priority: int
    target_price: Decimal
    confidence: Decimal
    wave_degree: str
    description: str | None


@dataclass(frozen=True, slots=True)
class ChartForecastScenario:
    """Immutable forecast scenario payload for chart overlays and legends."""

    scenario_type: str
    expected_next_wave: str
    confidence: Decimal
    reasoning: tuple[str, ...]
    projection_targets: tuple[ChartProjectionTarget, ...]


@dataclass(frozen=True, slots=True)
class ChartFibonacciProjection:
    """Immutable fibonacci projection payload for chart overlays."""

    level_ratio: Decimal
    price: Decimal
    direction: str
    reference_range: Decimal


@dataclass(frozen=True, slots=True)
class ChartSupportResistanceZone:
    """Immutable support/resistance zone payload for chart overlays."""

    zone_type: str
    lower_price: Decimal
    upper_price: Decimal
    touch_count: int
    first_timestamp: datetime
    last_timestamp: datetime
    pivot_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TimeframeChartData:
    """Immutable chart payload for one analyzed timeframe."""

    timeframe: str
    candles: tuple[ChartCandle, ...]
    swings: tuple[ChartSwing, ...]
    pivots: tuple[ChartPivot, ...]
    support_resistance_zones: tuple[ChartSupportResistanceZone, ...] = ()
    selected_waves: tuple[ChartWave, ...] = ()


@dataclass(frozen=True, slots=True)
class ChartDataContract:
    """Top-level immutable chart contract consumed by future renderers."""

    symbol: str
    generated_at: datetime
    timeframe_data: tuple[TimeframeChartData, ...]
    forecast_scenarios: tuple[ChartForecastScenario, ...]
    fibonacci_projections: tuple[ChartFibonacciProjection, ...]


def build_chart_data_contract(result: AnalysisApplicationResult) -> ChartDataContract:
    """Map analysis/forecast output to a deterministic renderer-agnostic chart contract."""

    timeframe_results = result.analysis.timeframe_results
    if not timeframe_results:
        message = "analysis must contain at least one timeframe result"
        raise DomainError(message)

    mapped_timeframes = tuple(
        mapped
        for mapped in (
            _map_timeframe_result(timeframe_result) for timeframe_result in timeframe_results
        )
        if mapped is not None
    )
    if not mapped_timeframes:
        message = "analysis must contain at least one timeframe with candle data"
        raise DomainError(message)

    scenarios = _map_forecast_scenarios(result)
    projections = _map_fibonacci_projections(result)
    return ChartDataContract(
        symbol=result.analysis.metadata.symbol.value,
        generated_at=result.analysis.metadata.completed_at,
        timeframe_data=mapped_timeframes,
        forecast_scenarios=scenarios,
        fibonacci_projections=projections,
    )


def _map_timeframe_result(timeframe_result: TimeframeAnalysisResult) -> TimeframeChartData | None:
    request = timeframe_result.request
    candles = tuple(
        sorted(
            (
                ChartCandle(
                    opened_at=candle.opened_at,
                    open_price=candle.open.value,
                    high_price=candle.high.value,
                    low_price=candle.low.value,
                    close_price=candle.close.value,
                )
                for candle in timeframe_result.candles
            ),
            key=lambda candle: (candle.opened_at, candle.open_price, candle.close_price),
        )
    )
    if not candles:
        return None

    swings = tuple(
        sorted(
            (
                ChartSwing(
                    swing_id=str(swing.id),
                    direction=swing.direction.value,
                    start_timestamp=swing.start_timestamp,
                    end_timestamp=swing.end_timestamp,
                    start_price=swing.start_pivot.price.value,
                    end_price=swing.end_pivot.price.value,
                    start_pivot_id=str(swing.start_pivot.id),
                    end_pivot_id=str(swing.end_pivot.id),
                )
                for swing in timeframe_result.prepared_swings
            ),
            key=lambda swing: (swing.start_timestamp, swing.end_timestamp, swing.swing_id),
        )
    )
    pivots = _map_pivots(timeframe_result.prepared_swings)
    support_resistance_zones = _map_support_resistance_zones(
        timeframe_result=timeframe_result,
    )
    selected_waves = _map_selected_waves(timeframe_result.selection_result)
    return TimeframeChartData(
        timeframe=request.timeframe.value,
        candles=candles,
        swings=swings,
        pivots=pivots,
        support_resistance_zones=support_resistance_zones,
        selected_waves=selected_waves,
    )


def _map_support_resistance_zones(
    *,
    timeframe_result: TimeframeAnalysisResult,
) -> tuple[ChartSupportResistanceZone, ...]:
    zones = derive_support_resistance_zones(
        candles=timeframe_result.candles,
        swings=timeframe_result.prepared_swings,
    )
    return tuple(
        ChartSupportResistanceZone(
            zone_type=zone.zone_type,
            lower_price=zone.lower_price,
            upper_price=zone.upper_price,
            touch_count=zone.touch_count,
            first_timestamp=zone.first_timestamp,
            last_timestamp=zone.last_timestamp,
            pivot_ids=zone.pivot_ids,
        )
        for zone in zones
    )


def _map_selected_waves(selection_result: SelectionResult) -> tuple[ChartWave, ...]:
    return tuple(
        ChartWave(
            wave_id=str(selected.wave_candidate.wave.id),
            wave_type=selected.wave_candidate.wave.wave_type.value,
            wave_degree=selected.wave_candidate.wave.degree.value,
            selection_rank=selected.rank,
            anchors=_map_wave_anchors(selected.wave_candidate.wave),
        )
        for selected in sorted(selection_result.selected_candidates, key=lambda item: item.rank)
    )


def _map_wave_anchors(wave: Wave) -> tuple[ChartWaveAnchor, ...]:
    anchors: list[ChartWaveAnchor] = []
    first_pivot = wave.swings[0].start_pivot
    anchors.append(
        ChartWaveAnchor(
            pivot_id=str(first_pivot.id),
            timestamp=first_pivot.timestamp,
            price=first_pivot.price.value,
            label=None,
        )
    )

    labels = _derive_wave_labels(wave.wave_type, len(wave.swings))
    for index, swing in enumerate(wave.swings):
        end_pivot = swing.end_pivot
        anchors.append(
            ChartWaveAnchor(
                pivot_id=str(end_pivot.id),
                timestamp=end_pivot.timestamp,
                price=end_pivot.price.value,
                label=labels[index],
            )
        )

    return tuple(anchors)


def _derive_wave_labels(wave_type: WaveType, swing_count: int) -> tuple[str | None, ...]:
    if wave_type is WaveType.IMPULSE and swing_count == _IMPULSE_WAVE_COUNT:
        return ("1", "2", "3", "4", "5")
    if wave_type is WaveType.CORRECTIVE and swing_count == _CORRECTIVE_WAVE_COUNT:
        return ("A", "B", "C")
    return tuple(None for _ in range(swing_count))


def _map_pivots(swings: tuple[Swing, ...]) -> tuple[ChartPivot, ...]:
    pivot_index: dict[str, ChartPivot] = {}

    for swing in swings:
        for pivot in (swing.start_pivot, swing.end_pivot):
            pivot_id = str(pivot.id)
            mapped = ChartPivot(
                pivot_id=pivot_id,
                timestamp=pivot.timestamp,
                price=pivot.price.value,
                pivot_type=pivot.pivot_type.value,
            )
            existing = pivot_index.get(pivot_id)
            if existing is not None and existing != mapped:
                message = f"pivot id '{pivot_id}' has conflicting chart coordinates"
                raise DomainError(message)
            pivot_index[pivot_id] = mapped

    return tuple(
        sorted(
            pivot_index.values(),
            key=lambda pivot: (pivot.timestamp, pivot.pivot_type, pivot.pivot_id),
        )
    )


def _map_forecast_scenarios(
    result: AnalysisApplicationResult,
) -> tuple[ChartForecastScenario, ...]:
    forecast = result.forecast
    scenarios = []

    if forecast.primary_scenario is not None:
        scenarios.append(forecast.primary_scenario)
    scenarios.extend(forecast.alternative_scenarios)

    return tuple(
        ChartForecastScenario(
            scenario_type=scenario.scenario_type.value,
            expected_next_wave=scenario.expected_next_wave,
            confidence=scenario.confidence,
            reasoning=scenario.reasoning,
            projection_targets=tuple(
                ChartProjectionTarget(
                    priority=target.priority,
                    target_price=target.target_price.value,
                    confidence=target.confidence,
                    wave_degree=target.wave_degree.value,
                    description=target.description,
                )
                for target in sorted(
                    scenario.projection_targets,
                    key=lambda target: target.priority,
                )
            ),
        )
        for scenario in scenarios
    )


def _map_fibonacci_projections(
    result: AnalysisApplicationResult,
) -> tuple[ChartFibonacciProjection, ...]:
    return tuple(
        ChartFibonacciProjection(
            level_ratio=projection.level.ratio,
            price=projection.price.value,
            direction=projection.direction.value,
            reference_range=projection.reference_range,
        )
        for projection in sorted(
            result.forecast.projections,
            key=lambda projection: (
                projection.level.ratio,
                projection.direction.value,
                projection.price.value,
            ),
        )
    )
