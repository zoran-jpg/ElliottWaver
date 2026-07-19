from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.detection.wave_detector import WaveDetector
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing
from elliottwaver.domain.rules.wave_rules import Wave2RetracementRule, WaveRule, WaveRuleSet


def make_pivot(
    *,
    pivot_id: EntityId,
    pivot_type: PivotType,
    price: str,
    when: datetime,
    symbol: Symbol | None = None,
    timeframe: Timeframe = Timeframe.ONE_HOUR,
) -> Pivot:
    return Pivot(
        id=pivot_id,
        symbol=symbol or Symbol("EURUSD"),
        timeframe=timeframe,
        timestamp=when,
        price=Price.parse(price),
        pivot_type=pivot_type,
    )


def make_connected_swings(
    *,
    prices: tuple[str, ...],
    symbol: Symbol | None = None,
    timeframe: Timeframe = Timeframe.ONE_HOUR,
) -> tuple[Swing, ...]:
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    pivots: list[Pivot] = []

    for index, price in enumerate(prices):
        pivot_type = PivotType.LOW if index % 2 == 0 else PivotType.HIGH
        pivots.append(
            make_pivot(
                pivot_id=EntityId.new(),
                pivot_type=pivot_type,
                price=price,
                when=base_time + timedelta(hours=index),
                symbol=symbol,
                timeframe=timeframe,
            )
        )

    return tuple(
        Swing(id=EntityId.new(), start_pivot=pivots[index], end_pivot=pivots[index + 1])
        for index in range(len(pivots) - 1)
    )


def make_wave2_rule_set() -> WaveRuleSet:
    rules: tuple[WaveRule, ...] = (cast("WaveRule", Wave2RetracementRule()),)
    return WaveRuleSet(rules=rules)


def test_empty_swing_sequence_returns_empty_result() -> None:
    result = WaveDetector().detect(())

    assert result.candidates == ()
    assert result.valid_candidates == ()
    assert result.invalid_candidates == ()


def test_valid_single_candidate() -> None:
    swings = make_connected_swings(prices=("100", "120", "105"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())

    result = detector.detect(swings)

    assert len(result.candidates) == 1
    assert result.candidates[0].is_valid is True


def test_multiple_candidates_are_supported() -> None:
    swings = make_connected_swings(prices=("100", "120", "108", "132"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())

    result = detector.detect(swings)

    assert len(result.candidates) == 3


def test_valid_and_invalid_candidates_in_same_result() -> None:
    swings = make_connected_swings(prices=("100", "120", "105", "122", "95", "130"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())

    result = detector.detect(swings)

    assert len(result.valid_candidates) > 0
    assert len(result.invalid_candidates) > 0


def test_rule_set_integration_reports_violations() -> None:
    swings = make_connected_swings(prices=("100", "120", "95"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())

    result = detector.detect(swings)

    assert result.candidates[0].is_invalid is True
    assert result.candidates[0].rule_result.violations[0].rule_name == "wave2_retracement_rule"


def test_non_connected_swings_do_not_crash() -> None:
    first_chain = make_connected_swings(prices=("100", "120", "105"))
    second_chain = make_connected_swings(prices=("200", "230", "210"))

    mixed = (first_chain[0], second_chain[0])
    result = WaveDetector().detect(mixed)

    assert result.candidates == ()


def test_different_symbols_split_chains() -> None:
    symbol_a = Symbol("EURUSD")
    symbol_b = Symbol("USDJPY")
    first = make_connected_swings(prices=("100", "120"), symbol=symbol_a)[0]
    second = make_connected_swings(prices=("120", "135"), symbol=symbol_b)[0]

    result = WaveDetector().detect((first, second))

    assert result.candidates == ()


def test_different_timeframes_split_chains() -> None:
    first = make_connected_swings(prices=("100", "120"), timeframe=Timeframe.ONE_HOUR)[0]
    second = make_connected_swings(prices=("120", "135"), timeframe=Timeframe.FIVE_MINUTES)[0]

    result = WaveDetector().detect((first, second))

    assert result.candidates == ()


def test_wrong_input_order_does_not_raise() -> None:
    swings = make_connected_swings(prices=("100", "120", "105"))

    result = WaveDetector().detect(tuple(reversed(swings)))

    assert result.candidates == ()


def test_detection_result_has_no_duplicates() -> None:
    swings = make_connected_swings(prices=("100", "120", "108", "132"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())

    result = detector.detect(swings)
    sequence_keys = [
        tuple(str(swing.id) for swing in candidate.wave.swings) for candidate in result.candidates
    ]

    assert len(sequence_keys) == len(set(sequence_keys))


def test_detection_order_is_deterministic() -> None:
    swings = make_connected_swings(prices=("100", "120", "108", "132", "121", "140"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())

    first_result = detector.detect(swings)
    second_result = detector.detect(swings)

    first_sequences = [
        tuple(str(swing.id) for swing in candidate.wave.swings)
        for candidate in first_result.candidates
    ]
    second_sequences = [
        tuple(str(swing.id) for swing in candidate.wave.swings)
        for candidate in second_result.candidates
    ]

    assert first_sequences == second_sequences
    assert [candidate.wave.id for candidate in first_result.candidates] == [
        candidate.wave.id for candidate in second_result.candidates
    ]


def test_immutability_for_candidate_and_result() -> None:
    swings = make_connected_swings(prices=("100", "120", "105"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())
    result = detector.detect(swings)
    candidate = result.candidates[0]
    wave_attr = "wave"
    candidates_attr = "candidates"

    with pytest.raises(FrozenInstanceError):
        candidate.__setattr__(wave_attr, candidate.wave)

    with pytest.raises(FrozenInstanceError):
        result.__setattr__(candidates_attr, result.candidates)


def test_wave_candidate_validity_matches_rule_result() -> None:
    swings = make_connected_swings(prices=("100", "120", "95"))
    detector = WaveDetector(rule_set=make_wave2_rule_set())

    candidate = detector.detect(swings).candidates[0]

    assert candidate.is_valid is candidate.rule_result.is_valid
    assert candidate.is_invalid is candidate.rule_result.is_invalid
