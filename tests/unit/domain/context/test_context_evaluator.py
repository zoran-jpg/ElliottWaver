from __future__ import annotations

from decimal import Decimal

import pytest

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.confluence import ConfluenceSeverity
from elliottwaver.domain.context import CompletionLevel, ContextEvaluator, ContextStrength

from .helpers import (
    make_confluence_result,
    make_selected_wave_candidate,
    make_trend_hierarchy,
)


def test_context_evaluator_handles_missing_trend() -> None:
    evaluator = ContextEvaluator()
    selected = make_selected_wave_candidate(direction="up", score_percent="80")

    trend_alignment = evaluator.evaluate_trend_alignment(
        selected_wave=selected,
        trend_hierarchy=None,
    )

    assert trend_alignment is None


def test_context_evaluator_detects_aligned_and_misaligned_trend() -> None:
    evaluator = ContextEvaluator()

    aligned = evaluator.evaluate_trend_alignment(
        selected_wave=make_selected_wave_candidate(direction="up"),
        trend_hierarchy=make_trend_hierarchy(root_direction="up", child_direction="up"),
    )
    misaligned = evaluator.evaluate_trend_alignment(
        selected_wave=make_selected_wave_candidate(direction="down"),
        trend_hierarchy=make_trend_hierarchy(root_direction="up", child_direction="up"),
    )

    assert aligned is True
    assert misaligned is False


def test_context_evaluator_classifies_completion_levels() -> None:
    evaluator = ContextEvaluator()

    assert (
        evaluator.evaluate_completion_level(
            confluence_score=Decimal("0"),
            structural_quality=Decimal("20"),
        )
        is CompletionLevel.EARLY
    )
    assert (
        evaluator.evaluate_completion_level(
            confluence_score=Decimal("40"),
            structural_quality=Decimal("50"),
        )
        is CompletionLevel.DEVELOPING
    )
    assert (
        evaluator.evaluate_completion_level(
            confluence_score=Decimal("70"),
            structural_quality=Decimal("70"),
        )
        is CompletionLevel.MATURE
    )
    assert (
        evaluator.evaluate_completion_level(
            confluence_score=Decimal("90"),
            structural_quality=Decimal("90"),
        )
        is CompletionLevel.COMPLETED
    )


def test_context_evaluator_weak_confluence_and_low_confidence() -> None:
    evaluator = ContextEvaluator()
    selected = make_selected_wave_candidate(score_percent="40", violations=2)
    hierarchy = make_trend_hierarchy(root_direction="up", child_direction="down", valid=False)
    confluence = make_confluence_result(
        confluence_percent="10",
        conflict_severity=ConfluenceSeverity.CRITICAL,
    )

    trend_alignment = evaluator.evaluate_trend_alignment(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
    )
    confluence_score = evaluator.evaluate_confluence_score(confluence_result=confluence)
    structural_quality = evaluator.evaluate_structural_quality(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
        confluence_result=confluence,
    )
    confidence = evaluator.evaluate_confidence(
        selected_wave=selected,
        confluence_score=confluence_score,
        structural_quality=structural_quality,
        trend_alignment=trend_alignment,
    )
    strength = evaluator.evaluate_context_strength(confidence=confidence)

    assert confluence_score == Decimal("10")
    assert structural_quality < Decimal("60")
    assert confidence < Decimal("35")
    assert strength is ContextStrength.WEAK


def test_context_evaluator_strong_confluence_and_high_confidence() -> None:
    evaluator = ContextEvaluator()
    selected = make_selected_wave_candidate(score_percent="96", violations=0)
    hierarchy = make_trend_hierarchy(root_direction="up", child_direction="up", valid=True)
    confluence = make_confluence_result(confluence_percent="92")

    trend_alignment = evaluator.evaluate_trend_alignment(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
    )
    confluence_score = evaluator.evaluate_confluence_score(confluence_result=confluence)
    structural_quality = evaluator.evaluate_structural_quality(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
        confluence_result=confluence,
    )
    confidence = evaluator.evaluate_confidence(
        selected_wave=selected,
        confluence_score=confluence_score,
        structural_quality=structural_quality,
        trend_alignment=trend_alignment,
    )
    strength = evaluator.evaluate_context_strength(confidence=confidence)

    assert confluence_score == Decimal("92")
    assert structural_quality == Decimal("100")
    assert confidence > Decimal("80")
    assert strength is ContextStrength.VERY_STRONG


def test_context_evaluator_is_deterministic() -> None:
    evaluator = ContextEvaluator()
    selected = make_selected_wave_candidate(score_percent="88", violations=1)
    hierarchy = make_trend_hierarchy(root_direction="up", child_direction="up", valid=True)
    confluence = make_confluence_result(confluence_percent="65")

    first = (
        evaluator.evaluate_trend_alignment(
            selected_wave=selected,
            trend_hierarchy=hierarchy,
        ),
        evaluator.evaluate_confluence_score(confluence_result=confluence),
        evaluator.evaluate_structural_quality(
            selected_wave=selected,
            trend_hierarchy=hierarchy,
            confluence_result=confluence,
        ),
    )
    second = (
        evaluator.evaluate_trend_alignment(
            selected_wave=selected,
            trend_hierarchy=hierarchy,
        ),
        evaluator.evaluate_confluence_score(confluence_result=confluence),
        evaluator.evaluate_structural_quality(
            selected_wave=selected,
            trend_hierarchy=hierarchy,
            confluence_result=confluence,
        ),
    )

    assert first == second


def test_context_evaluator_rejects_non_finite_confluence_score() -> None:
    evaluator = ContextEvaluator()

    with pytest.raises(DomainError, match="percent value must be finite"):
        evaluator.evaluate_completion_level(
            confluence_score=Decimal("NaN"),
            structural_quality=Decimal("50"),
        )
