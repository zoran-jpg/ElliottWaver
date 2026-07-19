"""Rule foundation for Elliott wave validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from elliottwaver.domain.market.swing import SwingDirection
from elliottwaver.domain.market.wave import Wave, WaveType

if TYPE_CHECKING:
    from decimal import Decimal


_WAVE2_MIN_SWINGS = 2
_WAVE4_MIN_SWINGS = 4
_WAVE3_MIN_SWINGS = 5


@dataclass(frozen=True, slots=True)
class RuleViolation:
    """Represents a single business-rule violation."""

    rule_name: str
    message: str


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Aggregates violations reported by one or more rules."""

    violations: tuple[RuleViolation, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return True when no violations were reported."""

        return not self.violations

    @property
    def is_invalid(self) -> bool:
        """Return True when one or more violations were reported."""

        return bool(self.violations)

    def merge(self, other: RuleResult) -> RuleResult:
        """Return a merged result containing violations from both results."""

        return RuleResult(violations=self.violations + other.violations)


@runtime_checkable
class WaveRule(Protocol):
    """A single business rule that evaluates a wave."""

    name: str

    def evaluate(self, wave: Wave) -> RuleResult:
        """Evaluate the rule and return a result."""


@dataclass(frozen=True, slots=True)
class WaveRuleSet:
    """Executes multiple wave rules and aggregates all violations."""

    rules: tuple[WaveRule, ...] = ()

    def evaluate(self, wave: Wave) -> RuleResult:
        """Run all rules and return an aggregated result."""

        result = RuleResult()

        for rule in self.rules:
            result = result.merge(rule.evaluate(wave))

        return result


@dataclass(frozen=True, slots=True)
class Wave2RetracementRule:
    """Wave 2 must not retrace beyond the origin of Wave 1."""

    name: str = "wave2_retracement_rule"

    def evaluate(self, wave: Wave) -> RuleResult:
        if wave.wave_type is not WaveType.IMPULSE:
            return RuleResult()

        if len(wave.swings) < _WAVE2_MIN_SWINGS:
            violation = RuleViolation(
                rule_name=self.name,
                message="Wave2RetracementRule requires at least 2 swings",
            )
            return RuleResult(violations=(violation,))

        wave1 = wave.swings[0]
        wave2 = wave.swings[1]

        origin_price = wave1.start_pivot.price.value
        wave2_end_price = wave2.end_pivot.price.value

        is_beyond_origin = (
            wave1.direction is SwingDirection.UP and wave2_end_price < origin_price
        ) or (wave1.direction is SwingDirection.DOWN and wave2_end_price > origin_price)

        if not is_beyond_origin:
            return RuleResult()

        violation = RuleViolation(
            rule_name=self.name,
            message="Wave 2 retraced beyond the origin of Wave 1",
        )
        return RuleResult(violations=(violation,))


@dataclass(frozen=True, slots=True)
class Wave3NotShortestRule:
    """Wave 3 must not be the shortest among Waves 1, 3, and 5."""

    name: str = "wave3_not_shortest_rule"

    def evaluate(self, wave: Wave) -> RuleResult:
        if wave.wave_type is not WaveType.IMPULSE:
            return RuleResult()

        if len(wave.swings) < _WAVE3_MIN_SWINGS:
            violation = RuleViolation(
                rule_name=self.name,
                message="Wave3NotShortestRule requires at least 5 swings",
            )
            return RuleResult(violations=(violation,))

        wave1_length = wave.swings[0].absolute_price_change
        wave3_length = wave.swings[2].absolute_price_change
        wave5_length = wave.swings[4].absolute_price_change

        is_shortest = wave3_length < wave1_length and wave3_length < wave5_length

        if not is_shortest:
            return RuleResult()

        violation = RuleViolation(
            rule_name=self.name,
            message="Wave 3 is the shortest among Waves 1, 3, and 5",
        )
        return RuleResult(violations=(violation,))


@dataclass(frozen=True, slots=True)
class Wave4NoOverlapRule:
    """Wave 4 must not overlap the price range of Wave 1 in a standard impulse."""

    name: str = "wave4_no_overlap_rule"

    def evaluate(self, wave: Wave) -> RuleResult:
        if wave.wave_type is not WaveType.IMPULSE:
            return RuleResult()

        if len(wave.swings) < _WAVE4_MIN_SWINGS:
            violation = RuleViolation(
                rule_name=self.name,
                message="Wave4NoOverlapRule requires at least 4 swings",
            )
            return RuleResult(violations=(violation,))

        wave1_start = wave.swings[0].start_pivot.price.value
        wave1_end = wave.swings[0].end_pivot.price.value
        wave4_start = wave.swings[3].start_pivot.price.value
        wave4_end = wave.swings[3].end_pivot.price.value

        wave1_low, wave1_high = _ordered_bounds(wave1_start, wave1_end)
        wave4_low, wave4_high = _ordered_bounds(wave4_start, wave4_end)

        overlaps = max(wave1_low, wave4_low) <= min(wave1_high, wave4_high)

        if not overlaps:
            return RuleResult()

        violation = RuleViolation(
            rule_name=self.name,
            message="Wave 4 overlaps the price range of Wave 1",
        )
        return RuleResult(violations=(violation,))


def _ordered_bounds(first: Decimal, second: Decimal) -> tuple[Decimal, Decimal]:
    """Return values ordered as (low, high)."""

    return (first, second) if first <= second else (second, first)
