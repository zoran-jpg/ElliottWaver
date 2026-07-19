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
from elliottwaver.domain.rules.wave_rules import RuleResult, RuleViolation
from elliottwaver.domain.scoring.wave_scorer import (
    ScoreComponent,
    ScoringConfig,
    ScoringResult,
    WaveScore,
    WaveScorer,
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


def make_candidate(
    *, prices: tuple[str, str, str, str, str, str], rule_result: RuleResult | None = None
) -> WaveCandidate:
    base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
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
    return WaveCandidate(wave=wave, rule_result=rule_result or RuleResult())


def make_raw_swing(*, start: Pivot, end: Pivot) -> Swing:
    swing = object.__new__(Swing)
    object.__setattr__(swing, "id", EntityId.new())
    object.__setattr__(swing, "start_pivot", start)
    object.__setattr__(swing, "end_pivot", end)
    return swing


def test_score_component_validation() -> None:
    component = ScoreComponent(
        name="swing_symmetry",
        weight=Decimal("0.20"),
        value=Decimal("0.50"),
        max_value=Decimal("1.00"),
    )

    assert component.normalized == Decimal("0.5")
    assert component.weighted_score == Decimal("0.10")


def test_score_component_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="weight"):
        ScoreComponent("x", Decimal("-0.1"), Decimal("0.5"), Decimal("1.0"))

    with pytest.raises(ValueError, match="max_value"):
        ScoreComponent("x", Decimal("0.1"), Decimal("0.5"), Decimal("0"))

    with pytest.raises(ValueError, match="within"):
        ScoreComponent("x", Decimal("0.1"), Decimal("1.5"), Decimal("1.0"))


def test_wave_score_percentage_and_comparison() -> None:
    high = WaveScore.from_components(
        (
            ScoreComponent("a", Decimal("1.0"), Decimal("1.0"), Decimal("1.0")),
            ScoreComponent("b", Decimal("1.0"), Decimal("1.0"), Decimal("1.0")),
        )
    )
    low = WaveScore.from_components(
        (
            ScoreComponent("a", Decimal("1.0"), Decimal("0.3"), Decimal("1.0")),
            ScoreComponent("b", Decimal("1.0"), Decimal("0.4"), Decimal("1.0")),
        )
    )

    assert high.percentage == Decimal("100")
    assert high > low


def test_wave_score_rejects_invalid_values() -> None:
    component = ScoreComponent("x", Decimal("1.0"), Decimal("1.0"), Decimal("1.0"))

    with pytest.raises(ValueError, match="total_score"):
        WaveScore(total_score=Decimal("-1"), components=(component,), percentage=Decimal("0"))

    with pytest.raises(ValueError, match="percentage"):
        WaveScore(total_score=Decimal("1"), components=(component,), percentage=Decimal("101"))


def test_wave_score_zero_weight_and_non_score_comparison() -> None:
    zero_weight = WaveScore.from_components(
        (ScoreComponent("x", Decimal("0.0"), Decimal("0.5"), Decimal("1.0")),)
    )

    assert zero_weight.total_score == Decimal("0")
    assert zero_weight.percentage == Decimal("0")
    assert zero_weight.__lt__("not-a-score") is NotImplemented


def test_wave_scorer_scores_only_valid_candidates() -> None:
    valid_candidate = make_candidate(prices=("100", "120", "108", "132", "121", "140"))
    invalid_candidate = make_candidate(
        prices=("100", "120", "108", "132", "121", "140"),
        rule_result=RuleResult(
            violations=(RuleViolation(rule_name="x", message="invalid"),),
        ),
    )

    result = WaveScorer().score((valid_candidate, invalid_candidate))

    assert len(result.scored_candidates) == 1
    assert result.scored_candidates[0].candidate.wave.id == valid_candidate.wave.id


def test_scoring_result_sorting_descending() -> None:
    better = make_candidate(prices=("100", "130", "112", "150", "128", "165"))
    worse = make_candidate(prices=("100", "110", "109", "113", "112", "114"))

    result = WaveScorer().score((worse, better))

    assert len(result.scored_candidates) == 2
    assert result.scored_candidates[0].score >= result.scored_candidates[1].score


def test_scoring_result_tie_is_deterministic() -> None:
    first = make_candidate(prices=("100", "120", "108", "132", "121", "140"))
    second = make_candidate(prices=("200", "220", "208", "232", "221", "240"))

    scorer = WaveScorer(config=ScoringConfig(rule_compliance_weight=Decimal("0.00")))
    result1 = scorer.score((first, second))
    result2 = scorer.score((first, second))

    ids1 = [str(item.candidate.wave.id) for item in result1.scored_candidates]
    ids2 = [str(item.candidate.wave.id) for item in result2.scored_candidates]

    assert ids1 == ids2


def test_deterministic_scores_for_identical_input() -> None:
    candidate = make_candidate(prices=("100", "120", "108", "132", "121", "140"))
    scorer = WaveScorer()

    first = scorer.score((candidate,)).scores[0]
    second = scorer.score((candidate,)).scores[0]

    assert first.total_score == second.total_score
    assert first.percentage == second.percentage
    assert first.components == second.components


def test_different_score_combinations_change_ranking() -> None:
    a = make_candidate(prices=("100", "140", "115", "165", "140", "180"))
    b = make_candidate(prices=("100", "115", "110", "130", "125", "135"))

    result = WaveScorer().score((a, b))

    assert result.scored_candidates[0].score != result.scored_candidates[1].score


def test_internal_edge_paths_for_component_scoring() -> None:
    scorer = WaveScorer()
    candidate = make_candidate(prices=("100", "120", "108", "132", "121", "140"))

    assert scorer._score_wave_proportions(candidate.wave.swings[:3]) == Decimal("0")
    assert scorer._score_impulse_consistency(()) == Decimal("0")

    point_in_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    start = make_pivot(
        pivot_id=EntityId.new(),
        pivot_type=PivotType.LOW,
        price="100",
        when=point_in_time,
    )
    end = make_pivot(
        pivot_id=EntityId.new(),
        pivot_type=PivotType.HIGH,
        price="110",
        when=point_in_time,
    )
    raw_swing = make_raw_swing(start=start, end=end)

    assert scorer._score_swing_symmetry((raw_swing,)) == Decimal("0")


def test_empty_input_returns_empty_scoring_result() -> None:
    result = WaveScorer().score(())

    assert result.scored_candidates == ()
    assert result.scores == ()


def test_results_are_immutable() -> None:
    candidate = make_candidate(prices=("100", "120", "108", "132", "121", "140"))
    scored = WaveScorer().score((candidate,))
    scored_candidates_attr = "scored_candidates"
    score_attr = "score"

    with pytest.raises(FrozenInstanceError):
        scored.__setattr__(scored_candidates_attr, ())

    with pytest.raises(FrozenInstanceError):
        scored.scored_candidates[0].__setattr__(score_attr, scored.scored_candidates[0].score)


def test_no_duplicate_wave_ids_in_scoring_result() -> None:
    candidate = make_candidate(prices=("100", "120", "108", "132", "121", "140"))

    result = WaveScorer().score((candidate, candidate))

    assert len(result.scored_candidates) == 1


def test_scoring_result_wrapper_sorts_input() -> None:
    candidate_a = make_candidate(prices=("100", "120", "108", "132", "121", "140"))
    candidate_b = make_candidate(prices=("100", "130", "112", "150", "128", "165"))

    scorer = WaveScorer()
    scored = scorer.score((candidate_a, candidate_b)).scored_candidates
    manual = ScoringResult(scored_candidates=tuple(reversed(scored)))

    assert manual.scored_candidates[0].score >= manual.scored_candidates[1].score
