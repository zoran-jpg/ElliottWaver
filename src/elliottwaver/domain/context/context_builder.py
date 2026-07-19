"""Elliott context builder over existing analysis artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from elliottwaver.domain.context.context_evaluator import ContextEvaluator
from elliottwaver.domain.context.elliott_context import ElliottContext

if TYPE_CHECKING:
    from elliottwaver.domain.confluence import MultiTimeframeConfluenceResult
    from elliottwaver.domain.multi_timeframe import Timeframe
    from elliottwaver.domain.selection import SelectedWaveCandidate
    from elliottwaver.domain.trend_hierarchy import TrendHierarchy


@dataclass(frozen=True, slots=True)
class ContextBuilder:
    """Build immutable context without mutating upstream analysis objects."""

    evaluator: ContextEvaluator = field(default_factory=ContextEvaluator)

    def build(
        self,
        *,
        selected_wave: SelectedWaveCandidate,
        trend_hierarchy: TrendHierarchy | None = None,
        confluence_result: MultiTimeframeConfluenceResult | None = None,
        trend_level: Timeframe | None = None,
    ) -> ElliottContext:
        """Build context from selection, hierarchy, and confluence outputs."""

        resolved_trend_level = trend_level
        if resolved_trend_level is None and trend_hierarchy is not None and trend_hierarchy.root:
            resolved_trend_level = trend_hierarchy.root.timeframe

        trend_alignment = self.evaluator.evaluate_trend_alignment(
            selected_wave=selected_wave,
            trend_hierarchy=trend_hierarchy,
        )
        confluence_score = self.evaluator.evaluate_confluence_score(
            confluence_result=confluence_result
        )
        structural_quality = self.evaluator.evaluate_structural_quality(
            selected_wave=selected_wave,
            trend_hierarchy=trend_hierarchy,
            confluence_result=confluence_result,
        )
        completion_level = self.evaluator.evaluate_completion_level(
            confluence_score=confluence_score,
            structural_quality=structural_quality,
        )
        confidence = self.evaluator.evaluate_confidence(
            selected_wave=selected_wave,
            confluence_score=confluence_score,
            structural_quality=structural_quality,
            trend_alignment=trend_alignment,
        )
        context_strength = self.evaluator.evaluate_context_strength(confidence=confidence)

        return ElliottContext(
            selected_wave=selected_wave,
            trend_alignment=trend_alignment,
            completion_level=completion_level,
            context_strength=context_strength,
            confidence=confidence,
            confluence_score=confluence_score,
            trend_level=resolved_trend_level,
            wave_degree=selected_wave.wave_candidate.wave.degree,
            structural_quality=structural_quality,
        )
