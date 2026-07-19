"""Deterministic context evaluation rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.confluence import ConfluenceSeverity, MultiTimeframeConfluenceResult
from elliottwaver.domain.context.completion_level import CompletionLevel
from elliottwaver.domain.context.context_strength import ContextStrength

if TYPE_CHECKING:
    from elliottwaver.domain.selection import SelectedWaveCandidate
    from elliottwaver.domain.trend_hierarchy import TrendHierarchy

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class ContextEvaluatorConfig:
    """Thresholds and deterministic weights for context evaluation."""

    confidence_weight_wave_score: Decimal = Decimal("0.45")
    confidence_weight_confluence: Decimal = Decimal("0.35")
    confidence_weight_structural_quality: Decimal = Decimal("0.20")
    trend_alignment_bonus: Decimal = Decimal("5")
    trend_alignment_penalty: Decimal = Decimal("10")
    missing_trend_penalty: Decimal = Decimal("5")
    rule_violation_penalty: Decimal = Decimal("20")
    invalid_hierarchy_penalty: Decimal = Decimal("15")
    conflict_penalty_info: Decimal = Decimal("2")
    conflict_penalty_warning: Decimal = Decimal("5")
    conflict_penalty_critical: Decimal = Decimal("10")
    completion_early_max: Decimal = Decimal("25")
    completion_developing_max: Decimal = Decimal("50")
    completion_mature_max: Decimal = Decimal("75")
    context_strength_weak_max: Decimal = Decimal("35")
    context_strength_moderate_max: Decimal = Decimal("60")
    context_strength_strong_max: Decimal = Decimal("80")

    def __post_init__(self) -> None:
        weights = (
            self.confidence_weight_wave_score,
            self.confidence_weight_confluence,
            self.confidence_weight_structural_quality,
        )
        if not all(weight.is_finite() for weight in weights):
            message = "confidence weights must be finite"
            raise DomainError(message)

        total_weight = sum(weights, _ZERO)
        if total_weight != Decimal("1"):
            message = "confidence weights must sum to 1"
            raise DomainError(message)


@dataclass(frozen=True, slots=True)
class ContextEvaluator:
    """Evaluate contextual indicators from already computed analysis outputs."""

    config: ContextEvaluatorConfig = field(default_factory=ContextEvaluatorConfig)

    def evaluate_trend_alignment(
        self,
        *,
        selected_wave: SelectedWaveCandidate,
        trend_hierarchy: TrendHierarchy | None,
    ) -> bool | None:
        """Return whether selected wave direction aligns with hierarchy trend."""

        if trend_hierarchy is None or not trend_hierarchy.nodes:
            return None

        reference_node = trend_hierarchy.root or trend_hierarchy.nodes[0]
        selected_direction = selected_wave.wave_candidate.wave.direction
        reference_direction = reference_node.selected_wave_candidate.wave_candidate.wave.direction
        return selected_direction == reference_direction

    def evaluate_confluence_score(
        self, *, confluence_result: MultiTimeframeConfluenceResult | None
    ) -> Decimal:
        """Return normalized confluence score percent."""

        if confluence_result is None:
            return _ZERO
        return _clamp_percent(confluence_result.confluence_percent)

    def evaluate_structural_quality(
        self,
        *,
        selected_wave: SelectedWaveCandidate,
        trend_hierarchy: TrendHierarchy | None,
        confluence_result: MultiTimeframeConfluenceResult | None,
    ) -> Decimal:
        """Return structural quality percent in [0, 100]."""

        quality = _HUNDRED
        quality -= self.config.rule_violation_penalty * Decimal(
            len(selected_wave.wave_candidate.rule_result.violations)
        )

        if trend_hierarchy is not None and not trend_hierarchy.is_valid:
            quality -= self.config.invalid_hierarchy_penalty

        if confluence_result is not None:
            for conflict in confluence_result.conflicts:
                if conflict.severity is ConfluenceSeverity.CRITICAL:
                    quality -= self.config.conflict_penalty_critical
                elif conflict.severity is ConfluenceSeverity.WARNING:
                    quality -= self.config.conflict_penalty_warning
                else:
                    quality -= self.config.conflict_penalty_info

        return _clamp_percent(quality)

    def evaluate_completion_level(
        self,
        *,
        confluence_score: Decimal,
        structural_quality: Decimal,
    ) -> CompletionLevel:
        """Return completion level based on maturity derived from context evidence."""

        maturity = _clamp_percent((confluence_score + structural_quality) / Decimal("2"))

        if maturity < self.config.completion_early_max:
            return CompletionLevel.EARLY
        if maturity < self.config.completion_developing_max:
            return CompletionLevel.DEVELOPING
        if maturity < self.config.completion_mature_max:
            return CompletionLevel.MATURE
        return CompletionLevel.COMPLETED

    def evaluate_confidence(
        self,
        *,
        selected_wave: SelectedWaveCandidate,
        confluence_score: Decimal,
        structural_quality: Decimal,
        trend_alignment: bool | None,
    ) -> Decimal:
        """Return confidence percent derived from wave quality and confluence evidence."""

        wave_score = _clamp_percent(selected_wave.wave_score.percentage)
        confluence = _clamp_percent(confluence_score)
        quality = _clamp_percent(structural_quality)

        confidence = (
            wave_score * self.config.confidence_weight_wave_score
            + confluence * self.config.confidence_weight_confluence
            + quality * self.config.confidence_weight_structural_quality
        )

        if trend_alignment is True:
            confidence += self.config.trend_alignment_bonus
        elif trend_alignment is False:
            confidence -= self.config.trend_alignment_penalty
        else:
            confidence -= self.config.missing_trend_penalty

        return _clamp_percent(confidence)

    def evaluate_context_strength(self, *, confidence: Decimal) -> ContextStrength:
        """Return qualitative strength from confidence."""

        normalized_confidence = _clamp_percent(confidence)

        if normalized_confidence < self.config.context_strength_weak_max:
            return ContextStrength.WEAK
        if normalized_confidence < self.config.context_strength_moderate_max:
            return ContextStrength.MODERATE
        if normalized_confidence < self.config.context_strength_strong_max:
            return ContextStrength.STRONG
        return ContextStrength.VERY_STRONG


def _clamp_percent(value: Decimal) -> Decimal:
    if not value.is_finite():
        message = "percent value must be finite"
        raise DomainError(message)
    if value < _ZERO:
        return _ZERO
    if value > _HUNDRED:
        return _HUNDRED
    return value
