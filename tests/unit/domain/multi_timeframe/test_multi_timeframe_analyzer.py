from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from elliottwaver.core.market import Symbol
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.multi_timeframe import (
    MultiTimeframeAnalysis,
    MultiTimeframeAnalyzer,
    Timeframe,
    TimeframeAnalysis,
)
from elliottwaver.domain.selection import SelectionResult


def make_selection_result(*, considered: int) -> SelectionResult:
    return SelectionResult(
        selected_candidates=(),
        policy_name="test_policy",
        considered_candidates=considered,
    )


def make_timeframe_analysis(
    *,
    timeframe: str,
    considered: int = 3,
    analysed_at: datetime | None = None,
) -> TimeframeAnalysis:
    return TimeframeAnalysis(
        timeframe=Timeframe.parse(timeframe),
        selection_result=make_selection_result(considered=considered),
        analysed_at=analysed_at or datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
        symbol=Symbol("EURUSD"),
        analysed_candidates_count=considered,
    )


def test_timeframe_supports_comparison_and_sorting() -> None:
    h1 = Timeframe.parse("H1")
    d1 = Timeframe.parse("D1")
    m5 = Timeframe.parse("M5")

    assert d1 < h1
    assert h1 < m5

    values = [h1, d1, m5]
    assert sorted(values) == [d1, h1, m5]


def test_timeframe_string_representation_and_validation() -> None:
    timeframe = Timeframe.parse(" m15 ")
    assert str(timeframe) == "M15"

    with pytest.raises(DomainError, match="Unsupported timeframe"):
        Timeframe.parse("H2")


def test_timeframe_analysis_valid_delegation_and_immutability() -> None:
    selection = make_selection_result(considered=4)
    analysis = TimeframeAnalysis(
        timeframe=Timeframe.parse("H1"),
        selection_result=selection,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
        symbol=Symbol("EURUSD"),
        analysed_candidates_count=4,
    )

    assert analysis.has_selection is selection.has_selection
    assert analysis.primary_candidate is selection.primary_candidate
    assert analysis.selected_count == selection.selected_count

    with pytest.raises(FrozenInstanceError):
        analysis.__setattr__("symbol", Symbol("GBPUSD"))


def test_timeframe_analysis_rejects_non_utc_and_count_mismatch() -> None:
    selection = make_selection_result(considered=2)

    with pytest.raises(DomainError, match="timezone-aware UTC"):
        TimeframeAnalysis(
            timeframe=Timeframe.parse("H1"),
            selection_result=selection,
            analysed_at=datetime(
                2026,
                7,
                19,
                12,
                0,
                tzinfo=timezone(timedelta(hours=1)),
            ),
            symbol=Symbol("EURUSD"),
            analysed_candidates_count=2,
        )

    with pytest.raises(DomainError, match="must equal"):
        TimeframeAnalysis(
            timeframe=Timeframe.parse("H1"),
            selection_result=selection,
            analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
            symbol=Symbol("EURUSD"),
            analysed_candidates_count=1,
        )


def test_multi_timeframe_analysis_empty() -> None:
    analysis = MultiTimeframeAnalysis()

    assert analysis.has_results is False
    assert analysis.highest_timeframe is None
    assert analysis.lowest_timeframe is None
    assert analysis.analysed_timeframes == ()


def test_multi_timeframe_analysis_sorts_and_exposes_bounds() -> None:
    d1 = make_timeframe_analysis(timeframe="D1")
    m15 = make_timeframe_analysis(timeframe="M15")
    h4 = make_timeframe_analysis(timeframe="H4")

    analysis = MultiTimeframeAnalysis(analyses=(m15, h4, d1))

    assert analysis.has_results is True
    assert analysis.analysed_timeframes == (
        Timeframe.parse("D1"),
        Timeframe.parse("H4"),
        Timeframe.parse("M15"),
    )
    assert analysis.highest_timeframe == Timeframe.parse("D1")
    assert analysis.lowest_timeframe == Timeframe.parse("M15")


def test_multi_timeframe_analysis_rejects_duplicate_timeframes() -> None:
    first = make_timeframe_analysis(timeframe="H1", considered=3)
    second = make_timeframe_analysis(timeframe="H1", considered=5)

    with pytest.raises(DomainError, match="duplicate timeframes"):
        MultiTimeframeAnalysis(analyses=(first, second))


def test_multi_timeframe_analyzer_handles_empty_single_and_multiple() -> None:
    analyzer = MultiTimeframeAnalyzer()
    now = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)

    empty = analyzer.analyze((), symbol=Symbol("EURUSD"), analysed_at=now)
    assert empty.analyses == ()

    single = analyzer.analyze(
        ((Timeframe.parse("H1"), make_selection_result(considered=2)),),
        symbol=Symbol("EURUSD"),
        analysed_at=now,
    )
    assert len(single.analyses) == 1
    assert single.analysed_timeframes == (Timeframe.parse("H1"),)

    multiple = analyzer.analyze(
        (
            (Timeframe.parse("M15"), make_selection_result(considered=1)),
            (Timeframe.parse("D1"), make_selection_result(considered=4)),
            (Timeframe.parse("H1"), make_selection_result(considered=2)),
        ),
        symbol=Symbol("EURUSD"),
        analysed_at=now,
    )
    assert multiple.analysed_timeframes == (
        Timeframe.parse("D1"),
        Timeframe.parse("H1"),
        Timeframe.parse("M15"),
    )


def test_multi_timeframe_analyzer_is_deterministic_and_keeps_inputs_unchanged() -> None:
    analyzer = MultiTimeframeAnalyzer()
    now = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)

    h1_selection = make_selection_result(considered=3)
    d1_selection = make_selection_result(considered=5)
    input_data = (
        (Timeframe.parse("H1"), h1_selection),
        (Timeframe.parse("D1"), d1_selection),
    )

    before_counts = tuple(item[1].considered_candidates for item in input_data)
    first = analyzer.analyze(input_data, symbol=Symbol("EURUSD"), analysed_at=now)
    second = analyzer.analyze(input_data, symbol=Symbol("EURUSD"), analysed_at=now)
    after_counts = tuple(item[1].considered_candidates for item in input_data)

    assert before_counts == after_counts
    assert first == second
    assert first.analyses[0].selection_result is d1_selection
    assert first.analyses[1].selection_result is h1_selection
