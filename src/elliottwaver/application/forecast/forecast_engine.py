"""Forecast Engine V1: deterministic scenario generation from completed analysis."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.application.analysis import AnalysisResponse, AnalysisStage
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.forecast import (
    ForecastResult,
    ForecastScenario,
    ProjectionQuality,
    ProjectionTarget,
    ScenarioType,
)
from elliottwaver.domain.market import Price
from elliottwaver.domain.projection import (
    FibonacciLevel,
    FibonacciProjection,
    FibonacciProjectionEngine,
    ProjectionDirection,
    ProjectionInput,
)

if TYPE_CHECKING:
    from elliottwaver.domain.market.wave import WaveDegree
    from elliottwaver.domain.selection import SelectedWaveCandidate

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_TWO = Decimal("2")
_WAVE_SCORE_WEIGHT = Decimal("0.7")
_CONFLUENCE_SCORE_WEIGHT = Decimal("0.3")
_ISSUE_PENALTY = Decimal("5")
_CONFLICT_PENALTY = Decimal("10")
_SECONDARY_TARGET_CONFIDENCE_DELTA = Decimal("10")
_ALTERNATIVE_CONFIDENCE_DELTA = Decimal("20")
_LOW_CONFIDENCE_THRESHOLD = Decimal("65")
_FIBONACCI_LEVELS: tuple[FibonacciLevel, ...] = (
    FibonacciLevel(Decimal("1.0")),
    FibonacciLevel(Decimal("1.618")),
)


@dataclass(frozen=True, slots=True)
class ForecastEngine:
    """Create a deterministic ForecastResult from an existing completed analysis."""

    def generate(self, analysis: AnalysisResponse | None) -> ForecastResult:
        """Generate V1 forecast scenarios from a completed analysis response."""

        if analysis is None:
            message = "analysis must not be None"
            raise DomainError(message)

        if analysis.stage is not AnalysisStage.COMPLETED:
            message = "analysis must be completed before forecast generation"
            raise DomainError(message)

        selected_wave = self._resolve_primary_selected_wave(analysis)
        if selected_wave is None:
            return ForecastResult(
                primary_scenario=None,
                alternative_scenarios=(),
                projection_quality=ProjectionQuality.LOW,
                overall_confidence=_ZERO,
                projections=(),
            )

        primary_confidence = self._compute_primary_confidence(analysis, selected_wave)
        primary_targets = self._create_primary_targets(selected_wave, primary_confidence)
        primary_reasoning = self._build_primary_reasoning(analysis, selected_wave)

        primary_scenario = ForecastScenario(
            scenario_type=ScenarioType.PRIMARY,
            expected_next_wave=self._expected_next_wave(selected_wave),
            confidence=primary_confidence,
            projection_targets=primary_targets,
            reasoning=primary_reasoning,
        )

        alternative_scenarios: tuple[ForecastScenario, ...] = ()
        if self._should_create_alternative(analysis, primary_confidence):
            alternative_scenarios = (
                self._create_alternative_scenario(analysis, selected_wave, primary_confidence),
            )

        overall_confidence = self._overall_confidence(primary_scenario, alternative_scenarios)
        projection_quality = self._projection_quality(overall_confidence)
        projections = self._create_fibonacci_projections(selected_wave)

        return ForecastResult(
            primary_scenario=primary_scenario,
            alternative_scenarios=alternative_scenarios,
            projection_quality=projection_quality,
            overall_confidence=overall_confidence,
            projections=projections,
        )

    def _resolve_primary_selected_wave(
        self, analysis: AnalysisResponse
    ) -> SelectedWaveCandidate | None:
        for timeframe_result in analysis.timeframe_results:
            primary_candidate = timeframe_result.selection_result.primary_candidate
            if primary_candidate is not None:
                return primary_candidate
        return None

    def _compute_primary_confidence(
        self,
        analysis: AnalysisResponse,
        selected_wave: SelectedWaveCandidate,
    ) -> Decimal:
        wave_score = selected_wave.wave_score.percentage
        confluence_score = (
            analysis.confluence_result.confluence_percent
            if analysis.confluence_result is not None
            else _ZERO
        )

        confidence = (wave_score * _WAVE_SCORE_WEIGHT) + (
            confluence_score * _CONFLUENCE_SCORE_WEIGHT
        )
        confidence -= Decimal(len(analysis.issues)) * _ISSUE_PENALTY

        if analysis.confluence_result is not None and analysis.confluence_result.has_conflicts:
            confidence -= _CONFLICT_PENALTY

        return self._clamp_percent(confidence)

    def _create_primary_targets(
        self,
        selected_wave: SelectedWaveCandidate,
        scenario_confidence: Decimal,
    ) -> tuple[ProjectionTarget, ...]:
        wave_degree, direction, anchor_price, move_size = self._projection_context(selected_wave)

        first_target_price = self._project_price(
            anchor_price=anchor_price,
            move_size=move_size,
            direction=direction,
            multiplier=Decimal("1"),
        )
        second_target_price = self._project_price(
            anchor_price=anchor_price,
            move_size=move_size,
            direction=direction,
            multiplier=Decimal("2"),
        )

        return (
            ProjectionTarget(
                target_price=first_target_price,
                wave_degree=wave_degree,
                priority=1,
                confidence=self._clamp_percent(scenario_confidence),
                description="Primary continuation target (1x last swing)",
            ),
            ProjectionTarget(
                target_price=second_target_price,
                wave_degree=wave_degree,
                priority=2,
                confidence=self._clamp_percent(
                    scenario_confidence - _SECONDARY_TARGET_CONFIDENCE_DELTA
                ),
                description="Primary continuation target (2x last swing)",
            ),
        )

    def _build_primary_reasoning(
        self,
        analysis: AnalysisResponse,
        selected_wave: SelectedWaveCandidate,
    ) -> tuple[str, ...]:
        reasoning: list[str] = [
            "Primary scenario derived from highest-priority selected wave.",
            f"Selected wave score: {selected_wave.wave_score.percentage}%.",
        ]

        if analysis.confluence_result is not None:
            reasoning.append(
                "Confluence score used for confidence: "
                f"{analysis.confluence_result.confluence_percent}%.",
            )
        else:
            reasoning.append("No confluence result available; confidence uses wave score only.")

        if analysis.issues:
            reasoning.append(
                "Analysis issues reduce confidence to keep V1 forecast conservative.",
            )

        return tuple(reasoning)

    def _should_create_alternative(
        self,
        analysis: AnalysisResponse,
        primary_confidence: Decimal,
    ) -> bool:
        if primary_confidence < _LOW_CONFIDENCE_THRESHOLD:
            return True

        if analysis.has_issues:
            return True

        return analysis.confluence_result is not None and analysis.confluence_result.has_conflicts

    def _create_alternative_scenario(
        self,
        analysis: AnalysisResponse,
        selected_wave: SelectedWaveCandidate,
        primary_confidence: Decimal,
    ) -> ForecastScenario:
        wave_degree, direction, anchor_price, move_size = self._projection_context(selected_wave)

        reverse_direction = "down" if direction == "up" else "up"
        retracement_target = self._project_price(
            anchor_price=anchor_price,
            move_size=move_size,
            direction=reverse_direction,
            multiplier=Decimal("0.5"),
        )

        alternative_confidence = self._clamp_percent(
            primary_confidence - _ALTERNATIVE_CONFIDENCE_DELTA
        )
        reasoning = self._build_alternative_reasoning(analysis)

        return ForecastScenario(
            scenario_type=ScenarioType.ALTERNATIVE,
            expected_next_wave="Alternative corrective path",
            confidence=alternative_confidence,
            projection_targets=(
                ProjectionTarget(
                    target_price=retracement_target,
                    wave_degree=wave_degree,
                    priority=1,
                    confidence=alternative_confidence,
                    description="Alternative retracement target (0.5x reverse move)",
                ),
            ),
            reasoning=reasoning,
        )

    def _projection_context(
        self,
        selected_wave: SelectedWaveCandidate,
    ) -> tuple[WaveDegree, str, Decimal, Decimal]:
        """Extract shared projection inputs from the selected wave."""

        wave = selected_wave.wave_candidate.wave
        last_swing = wave.swings[-1]
        return (
            wave.degree,
            wave.direction.value,
            last_swing.end_pivot.price.value,
            last_swing.absolute_price_change,
        )

    def _create_fibonacci_projections(
        self,
        selected_wave: SelectedWaveCandidate,
    ) -> tuple[FibonacciProjection, ...]:
        wave = selected_wave.wave_candidate.wave
        last_swing = wave.swings[-1]
        direction = (
            ProjectionDirection.UP
            if wave.direction.value == ProjectionDirection.UP.value
            else ProjectionDirection.DOWN
        )
        projection_input = ProjectionInput(
            start_price=last_swing.start_pivot.price,
            end_price=last_swing.end_pivot.price,
            projection_origin=last_swing.end_pivot.price,
            direction=direction,
        )
        return FibonacciProjectionEngine().project(
            projection_input=projection_input,
            levels=_FIBONACCI_LEVELS,
        )

    def _build_alternative_reasoning(self, analysis: AnalysisResponse) -> tuple[str, ...]:
        reasoning: list[str] = [
            "Alternative scenario is generated when confidence is reduced or conflicts exist.",
        ]

        if analysis.confluence_result is not None and analysis.confluence_result.has_conflicts:
            reasoning.append("Confluence conflicts detected; fallback path is included.")

        if analysis.issues:
            reasoning.append("Analysis issues detected; alternative path is kept active.")

        if len(reasoning) == 1:
            reasoning.append(
                "Primary confidence is below the minimum threshold for single-scenario output."
            )

        return tuple(reasoning)

    def _overall_confidence(
        self,
        primary_scenario: ForecastScenario,
        alternative_scenarios: tuple[ForecastScenario, ...],
    ) -> Decimal:
        if not alternative_scenarios:
            return primary_scenario.confidence

        alternative_mean = sum(
            (scenario.confidence for scenario in alternative_scenarios),
            _ZERO,
        ) / Decimal(len(alternative_scenarios))
        return self._clamp_percent((primary_scenario.confidence + alternative_mean) / _TWO)

    def _projection_quality(self, confidence: Decimal) -> ProjectionQuality:
        if confidence >= Decimal("85"):
            return ProjectionQuality.VERY_HIGH
        if confidence >= Decimal("70"):
            return ProjectionQuality.HIGH
        if confidence >= Decimal("50"):
            return ProjectionQuality.MEDIUM
        return ProjectionQuality.LOW

    def _expected_next_wave(self, selected_wave: SelectedWaveCandidate) -> str:
        wave = selected_wave.wave_candidate.wave
        direction = wave.direction.value
        return f"Continuation scenario for {wave.degree.value} degree ({direction} bias)"

    def _project_price(
        self,
        *,
        anchor_price: Decimal,
        move_size: Decimal,
        direction: str,
        multiplier: Decimal,
    ) -> Price:
        projected_move = move_size * multiplier
        if direction == "up":
            projected_value = anchor_price + projected_move
        else:
            projected_value = anchor_price - projected_move

        projected_value = max(projected_value, _ZERO)

        return Price.parse(projected_value)

    def _clamp_percent(self, value: Decimal) -> Decimal:
        if not value.is_finite():
            message = "percent value must be finite"
            raise DomainError(message)
        if value < _ZERO:
            return _ZERO
        if value > _HUNDRED:
            return _HUNDRED
        return value
