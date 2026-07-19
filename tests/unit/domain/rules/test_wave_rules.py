from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType
from elliottwaver.domain.rules.wave_rules import (
    RuleResult,
    RuleViolation,
    Wave2RetracementRule,
    Wave3NotShortestRule,
    Wave4NoOverlapRule,
    WaveRule,
    WaveRuleSet,
)


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


def make_impulse_wave(*, prices: tuple[str, str, str, str, str, str], bullish: bool = True) -> Wave:
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    pivot_types = (
        (
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
        )
        if bullish
        else (
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
        )
    )

    pivots = tuple(
        make_pivot(
            pivot_id=EntityId.new(),
            pivot_type=pivot_types[index],
            price=price,
            when=base_time + timedelta(hours=index),
        )
        for index, price in enumerate(prices)
    )

    swings = tuple(
        Swing(id=EntityId.new(), start_pivot=pivots[index], end_pivot=pivots[index + 1])
        for index in range(5)
    )

    return Wave(
        id=EntityId.new(),
        wave_type=WaveType.IMPULSE,
        degree=WaveDegree.PRIMARY,
        swings=swings,
    )


def test_rule_violation_content() -> None:
    violation = RuleViolation(
        rule_name="wave2_retracement_rule",
        message="Wave 2 retraced beyond the origin of Wave 1",
    )

    assert violation.rule_name == "wave2_retracement_rule"
    assert "retraced" in violation.message


def test_rule_result_valid_and_invalid() -> None:
    valid_result = RuleResult()
    invalid_result = RuleResult(
        violations=(
            RuleViolation(
                rule_name="wave4_no_overlap_rule",
                message="Wave 4 overlaps the price range of Wave 1",
            ),
        )
    )

    assert valid_result.is_valid is True
    assert valid_result.is_invalid is False
    assert invalid_result.is_valid is False
    assert invalid_result.is_invalid is True


def test_rule_result_is_immutable() -> None:
    result = RuleResult()
    violation = RuleViolation(rule_name="sample", message="sample")
    violations_attr = "violations"
    message_attr = "message"

    with pytest.raises(FrozenInstanceError):
        result.__setattr__(violations_attr, ())

    with pytest.raises(FrozenInstanceError):
        violation.__setattr__(message_attr, "changed")


def test_wave2_retracement_rule_valid_scenario() -> None:
    wave = make_impulse_wave(prices=("100", "120", "105", "135", "121", "150"))

    result = Wave2RetracementRule().evaluate(wave)

    assert result.is_valid is True


def test_wave2_retracement_rule_violation() -> None:
    wave = make_impulse_wave(prices=("100", "120", "95", "132", "121", "150"))

    result = Wave2RetracementRule().evaluate(wave)

    assert result.is_invalid is True
    assert result.violations[0].rule_name == "wave2_retracement_rule"


def test_wave3_not_shortest_rule_valid_scenario() -> None:
    wave = make_impulse_wave(prices=("100", "115", "108", "140", "130", "155"))

    result = Wave3NotShortestRule().evaluate(wave)

    assert result.is_valid is True


def test_wave3_not_shortest_rule_violation() -> None:
    wave = make_impulse_wave(prices=("100", "120", "112", "118", "111", "140"))

    result = Wave3NotShortestRule().evaluate(wave)

    assert result.is_invalid is True
    assert result.violations[0].rule_name == "wave3_not_shortest_rule"


def test_wave4_no_overlap_rule_valid_scenario() -> None:
    wave = make_impulse_wave(prices=("100", "120", "112", "135", "125", "150"))

    result = Wave4NoOverlapRule().evaluate(wave)

    assert result.is_valid is True


def test_wave4_no_overlap_rule_violation() -> None:
    wave = make_impulse_wave(prices=("100", "120", "112", "130", "110", "150"))

    result = Wave4NoOverlapRule().evaluate(wave)

    assert result.is_invalid is True
    assert result.violations[0].rule_name == "wave4_no_overlap_rule"


def test_empty_wave_rule_set_is_valid() -> None:
    wave = make_impulse_wave(prices=("100", "120", "112", "135", "125", "150"))

    result = WaveRuleSet().evaluate(wave)

    assert result.is_valid is True
    assert result.violations == ()


def test_wave_rule_set_aggregates_multiple_rules() -> None:
    wave = make_impulse_wave(prices=("100", "120", "95", "112", "105", "130"))
    rules: tuple[WaveRule, ...] = (
        cast("WaveRule", Wave2RetracementRule()),
        cast("WaveRule", Wave3NotShortestRule()),
        cast("WaveRule", Wave4NoOverlapRule()),
    )
    rule_set = WaveRuleSet(rules=rules)

    result = rule_set.evaluate(wave)

    assert result.is_invalid is True
    assert len(result.violations) == 3
    assert {violation.rule_name for violation in result.violations} == {
        "wave2_retracement_rule",
        "wave3_not_shortest_rule",
        "wave4_no_overlap_rule",
    }


def test_wave_rule_set_with_multiple_rules_valid_scenario() -> None:
    wave = make_impulse_wave(prices=("100", "120", "108", "140", "125", "160"))
    rules: tuple[WaveRule, ...] = (
        cast("WaveRule", Wave2RetracementRule()),
        cast("WaveRule", Wave3NotShortestRule()),
        cast("WaveRule", Wave4NoOverlapRule()),
    )
    rule_set = WaveRuleSet(rules=rules)

    result = rule_set.evaluate(wave)

    assert result.is_valid is True
