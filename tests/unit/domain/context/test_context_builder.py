from __future__ import annotations

from elliottwaver.domain.context import CompletionLevel, ContextBuilder, ContextStrength
from elliottwaver.domain.multi_timeframe import Timeframe

from .helpers import (
    make_confluence_result,
    make_selected_wave_candidate,
    make_trend_hierarchy,
)


def test_context_builder_builds_expected_context() -> None:
    builder = ContextBuilder()
    selected = make_selected_wave_candidate(direction="up", score_percent="90")
    hierarchy = make_trend_hierarchy(root_direction="up", child_direction="up")
    confluence = make_confluence_result(confluence_percent="82")

    context = builder.build(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
        confluence_result=confluence,
    )

    assert context.selected_wave == selected
    assert context.trend_alignment is True
    assert context.confluence_score == confluence.confluence_percent
    assert context.trend_level == Timeframe.parse("D1")
    assert context.wave_degree == selected.wave_candidate.wave.degree
    assert context.completion_level in (
        CompletionLevel.MATURE,
        CompletionLevel.COMPLETED,
    )
    assert context.context_strength in (
        ContextStrength.STRONG,
        ContextStrength.VERY_STRONG,
    )


def test_context_builder_handles_missing_trend_and_empty_inputs() -> None:
    builder = ContextBuilder()
    selected = make_selected_wave_candidate(direction="down", score_percent="55")

    context = builder.build(
        selected_wave=selected,
        trend_hierarchy=None,
        confluence_result=None,
    )

    assert context.trend_alignment is None
    assert context.trend_level is None
    assert context.confluence_score == 0


def test_context_builder_respects_explicit_trend_level() -> None:
    builder = ContextBuilder()
    selected = make_selected_wave_candidate(direction="up", score_percent="75")
    hierarchy = make_trend_hierarchy(root_direction="up", child_direction="up")

    context = builder.build(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
        confluence_result=None,
        trend_level=Timeframe.parse("H4"),
    )

    assert context.trend_level == Timeframe.parse("H4")


def test_context_builder_is_deterministic() -> None:
    builder = ContextBuilder()
    selected = make_selected_wave_candidate(direction="up", score_percent="88")
    hierarchy = make_trend_hierarchy(root_direction="up", child_direction="up")
    confluence = make_confluence_result(confluence_percent="70")

    first = builder.build(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
        confluence_result=confluence,
    )
    second = builder.build(
        selected_wave=selected,
        trend_hierarchy=hierarchy,
        confluence_result=confluence,
    )

    assert first == second
