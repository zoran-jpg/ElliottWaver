from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.detection.wave_detector import WaveCandidate
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType
from elliottwaver.domain.rules.wave_rules import RuleResult
from elliottwaver.domain.scoring import (
    ScoreComponent,
    ScoredWaveCandidate,
    ScoringResult,
    WaveScore,
)
from elliottwaver.domain.selection.wave_selector import (
    REASON_HIGHEST_SCORE,
    REASON_MINIMUM_SCORE_REACHED,
    REASON_SUFFICIENT_SCORE_GAP,
    MinimumScoreSelectionPolicy,
    ScoreGapSelectionPolicy,
    SelectedWaveCandidate,
    SelectionConfig,
    SelectionReason,
    SelectionResult,
    TopScoreSelectionPolicy,
    WaveSelector,
)


def make_pivot(
    *,
    pivot_id: EntityId,
    pivot_type: PivotType,
    price: str,
    when: datetime,
) -> Pivot:
    return Pivot(
        id=pivot_id,
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        timestamp=when,
        price=Price.parse(price),
        pivot_type=pivot_type,
    )


def make_wave_candidate(*, anchor: int) -> WaveCandidate:
    base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC) + timedelta(days=anchor)
    prices = ("100", "120", "108", "132", "121", "140")
    pivots = tuple(
        make_pivot(
            pivot_id=EntityId.new(),
            pivot_type=PivotType.LOW if idx % 2 == 0 else PivotType.HIGH,
            price=price,
            when=base + timedelta(hours=idx),
        )
        for idx, price in enumerate(prices)
    )
    swings = tuple(
        Swing(id=EntityId.new(), start_pivot=pivots[idx], end_pivot=pivots[idx + 1])
        for idx in range(5)
    )
    wave = Wave(
        id=EntityId.new(),
        wave_type=WaveType.IMPULSE,
        degree=WaveDegree.PRIMARY,
        swings=swings,
    )
    return WaveCandidate(wave=wave, rule_result=RuleResult())


def make_scored_candidate(*, anchor: int, percent: str) -> ScoredWaveCandidate:
    candidate = make_wave_candidate(anchor=anchor)
    percentage = Decimal(percent)
    component = ScoreComponent(
        name="score",
        weight=Decimal("1"),
        value=percentage,
        max_value=Decimal("100"),
    )
    score = WaveScore(
        total_score=percentage,
        components=(component,),
        percentage=percentage,
    )
    return ScoredWaveCandidate(candidate=candidate, score=score)


def make_scoring_result(*percentages: str) -> ScoringResult:
    scored = tuple(
        make_scored_candidate(anchor=index, percent=percent)
        for index, percent in enumerate(percentages)
    )
    return ScoringResult(scored_candidates=scored)


def test_selection_config_valid_and_immutable() -> None:
    config = SelectionConfig(
        minimum_score_percent=Decimal("60"),
        minimum_score_gap_percent=Decimal("4"),
        maximum_selected_candidates=2,
    )

    assert config.minimum_score_percent == Decimal("60")

    minimum_attr = "minimum_score_percent"
    with pytest.raises(FrozenInstanceError):
        config.__setattr__(minimum_attr, Decimal("50"))


def test_selection_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="minimum_score_percent"):
        SelectionConfig(minimum_score_percent=Decimal("-1"))

    with pytest.raises(ValueError, match="minimum_score_percent"):
        SelectionConfig(minimum_score_percent=Decimal("101"))

    with pytest.raises(ValueError, match="minimum_score_gap_percent"):
        SelectionConfig(minimum_score_gap_percent=Decimal("-1"))

    with pytest.raises(ValueError, match="maximum_selected_candidates"):
        SelectionConfig(maximum_selected_candidates=0)


def test_top_score_policy_empty_single_multiple_tie_and_stable_order() -> None:
    policy = TopScoreSelectionPolicy()
    config = SelectionConfig()

    assert policy.select(ScoringResult(), config) == ()

    single = make_scoring_result("91")
    assert policy.select(single, config)[0].scored_candidate.score.percentage == Decimal("91")

    multiple = make_scoring_result("95", "88", "72")
    assert policy.select(multiple, config)[0].scored_candidate is multiple.scored_candidates[0]

    tied = make_scoring_result("90", "90", "80")
    assert policy.select(tied, config)[0].scored_candidate is tied.scored_candidates[0]


def test_minimum_score_policy_variants_and_limit() -> None:
    policy = MinimumScoreSelectionPolicy()

    empty = policy.select(
        make_scoring_result("40", "35"),
        SelectionConfig(minimum_score_percent=Decimal("50")),
    )
    assert empty == ()

    exact = policy.select(
        make_scoring_result("50", "49"),
        SelectionConfig(minimum_score_percent=Decimal("50")),
    )
    assert len(exact) == 1

    multiple = policy.select(
        make_scoring_result("90", "85", "70", "60"),
        SelectionConfig(minimum_score_percent=Decimal("70"), maximum_selected_candidates=2),
    )
    assert len(multiple) == 2
    assert multiple[0].scored_candidate.score.percentage == Decimal("90")
    assert multiple[1].scored_candidate.score.percentage == Decimal("85")


def test_score_gap_policy_variants() -> None:
    policy = ScoreGapSelectionPolicy()

    assert policy.select(ScoringResult(), SelectionConfig()) == ()

    single = policy.select(make_scoring_result("90"), SelectionConfig())
    assert len(single) == 1

    exact = policy.select(
        make_scoring_result("90", "85"),
        SelectionConfig(minimum_score_gap_percent=Decimal("5")),
    )
    assert len(exact) == 1

    above = policy.select(
        make_scoring_result("90", "80"),
        SelectionConfig(minimum_score_gap_percent=Decimal("5")),
    )
    assert len(above) == 1

    below = policy.select(
        make_scoring_result("90", "89"),
        SelectionConfig(minimum_score_gap_percent=Decimal("5")),
    )
    assert below == ()

    tie = policy.select(
        make_scoring_result("90", "90"),
        SelectionConfig(minimum_score_gap_percent=Decimal("0.1")),
    )
    assert tie == ()


def test_selection_reason_codes_values_and_immutability() -> None:
    reason = SelectionReason(
        policy_name="top_score",
        reason_code=REASON_HIGHEST_SCORE,
        message="Picked best",
        metrics=(("score_percent", Decimal("91")),),
    )

    assert reason.reason_code in {
        REASON_HIGHEST_SCORE,
        REASON_MINIMUM_SCORE_REACHED,
        REASON_SUFFICIENT_SCORE_GAP,
    }
    assert reason.metrics[0][1] == Decimal("91")

    message_attr = "message"
    with pytest.raises(FrozenInstanceError):
        reason.__setattr__(message_attr, "changed")


def test_selected_wave_candidate_rank_delegation_and_immutability() -> None:
    scored = make_scored_candidate(anchor=1, percent="91")
    reason = SelectionReason(
        policy_name="top_score",
        reason_code=REASON_HIGHEST_SCORE,
        message="Picked best",
    )

    selected = TopScoreSelectionPolicy().select((scored,), SelectionConfig())[0]

    assert selected.rank == 1
    assert selected.wave_candidate is scored.candidate
    assert selected.wave_score is scored.score

    rank_attr = "rank"
    with pytest.raises(FrozenInstanceError):
        selected.__setattr__(rank_attr, 2)

    with pytest.raises(ValueError, match="rank"):
        SelectedWaveCandidate(scored_candidate=scored, reasons=(reason,), rank=0)


def test_selection_result_variants_and_immutability() -> None:
    empty = SelectionResult(selected_candidates=(), policy_name="x", considered_candidates=2)
    assert empty.is_empty is True
    assert empty.primary_candidate is None

    result = WaveSelector().select(make_scoring_result("91", "88"))
    assert result.has_selection is True
    assert result.selected_count == 1
    assert result.primary_candidate is result.selected_candidates[0]
    assert result.considered_candidates == 2

    selected_attr = "selected_candidates"
    with pytest.raises(FrozenInstanceError):
        result.__setattr__(selected_attr, ())

    duplicate = SelectedWaveCandidate(
        scored_candidate=result.selected_candidates[0].scored_candidate,
        reasons=result.selected_candidates[0].reasons,
        rank=2,
    )

    with pytest.raises(ValueError, match="duplicates"):
        SelectionResult(
            selected_candidates=(result.selected_candidates[0], duplicate),
            policy_name="x",
            considered_candidates=2,
        )


def test_wave_selector_policy_delegation_and_determinism() -> None:
    scoring_result = make_scoring_result("91", "88", "70")

    top_result = WaveSelector(
        policy=TopScoreSelectionPolicy(),
        config=SelectionConfig(maximum_selected_candidates=2),
    ).select(scoring_result)

    min_result = WaveSelector(
        policy=MinimumScoreSelectionPolicy(),
        config=SelectionConfig(minimum_score_percent=Decimal("80"), maximum_selected_candidates=3),
    ).select(scoring_result)

    assert top_result.selected_count == 1
    assert min_result.selected_count == 2

    original_ids = tuple(str(item.candidate.wave.id) for item in scoring_result.scored_candidates)
    WaveSelector(policy=TopScoreSelectionPolicy()).select(scoring_result)
    after_ids = tuple(str(item.candidate.wave.id) for item in scoring_result.scored_candidates)
    assert original_ids == after_ids

    first = WaveSelector(policy=MinimumScoreSelectionPolicy()).select(scoring_result)
    second = WaveSelector(policy=MinimumScoreSelectionPolicy()).select(scoring_result)
    assert first.selected_candidates == second.selected_candidates


def test_no_score_recalculation_and_policy_input_variants() -> None:
    scoring_result = make_scoring_result("91", "88")
    selector = WaveSelector(policy=TopScoreSelectionPolicy())
    selection = selector.select(scoring_result)

    assert selection.primary_candidate is not None
    assert selection.primary_candidate.scored_candidate is scoring_result.scored_candidates[0]

    from_tuple = TopScoreSelectionPolicy().select(
        scoring_result.scored_candidates,
        SelectionConfig(),
    )
    from_result = TopScoreSelectionPolicy().select(scoring_result, SelectionConfig())
    assert from_tuple == from_result
