"""Deterministic wave-candidate detection from swing sequences."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast
from uuid import NAMESPACE_URL, uuid5

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType
from elliottwaver.domain.rules.wave_rules import (
    RuleResult,
    Wave2RetracementRule,
    Wave3NotShortestRule,
    Wave4NoOverlapRule,
    WaveRuleSet,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from elliottwaver.domain.market.swing import Swing
    from elliottwaver.domain.rules.wave_rules import WaveRule


_MIN_SWINGS_PER_CANDIDATE = 2


@dataclass(frozen=True, slots=True)
class WaveCandidate:
    """A detected wave candidate and its validation outcome."""

    wave: Wave
    rule_result: RuleResult

    @property
    def is_valid(self) -> bool:
        """Return True when all configured rules are satisfied."""

        return self.rule_result.is_valid

    @property
    def is_invalid(self) -> bool:
        """Return True when one or more rules are violated."""

        return self.rule_result.is_invalid


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Collection of detected wave candidates."""

    candidates: tuple[WaveCandidate, ...] = ()

    @property
    def valid_candidates(self) -> tuple[WaveCandidate, ...]:
        """Return all valid candidates in input order."""

        return tuple(candidate for candidate in self.candidates if candidate.is_valid)

    @property
    def invalid_candidates(self) -> tuple[WaveCandidate, ...]:
        """Return all invalid candidates in input order."""

        return tuple(candidate for candidate in self.candidates if candidate.is_invalid)


def _default_rule_set() -> WaveRuleSet:
    """Return the default rule set for candidate validation."""

    rules: tuple[WaveRule, ...] = (
        cast("WaveRule", Wave2RetracementRule()),
        cast("WaveRule", Wave3NotShortestRule()),
        cast("WaveRule", Wave4NoOverlapRule()),
    )
    return WaveRuleSet(rules=rules)


@dataclass(frozen=True, slots=True)
class WaveDetector:
    """Create deterministic wave candidates from ordered swing inputs."""

    rule_set: WaveRuleSet = field(default_factory=_default_rule_set)
    wave_type: WaveType = WaveType.IMPULSE
    wave_degree: WaveDegree = WaveDegree.PRIMARY

    def detect(self, swings: Sequence[Swing]) -> DetectionResult:
        """Detect and validate wave candidates from an ordered swing sequence."""

        ordered_swings = tuple(swings)

        if not ordered_swings:
            return DetectionResult()

        candidates: list[WaveCandidate] = []
        seen_sequences: set[tuple[str, ...]] = set()

        for chain in self._extract_connected_chains(ordered_swings):
            for window in _sliding_windows(chain, _MIN_SWINGS_PER_CANDIDATE):
                sequence_key = tuple(str(swing.id) for swing in window)
                if sequence_key in seen_sequences:
                    continue

                try:
                    wave = Wave(
                        id=_deterministic_wave_id(sequence_key),
                        wave_type=self.wave_type,
                        degree=self.wave_degree,
                        swings=window,
                    )
                except DomainError:
                    # Ignore constructively invalid wave windows and continue detection.
                    continue

                rule_result = self.rule_set.evaluate(wave)
                candidates.append(WaveCandidate(wave=wave, rule_result=rule_result))
                seen_sequences.add(sequence_key)

        return DetectionResult(candidates=tuple(candidates))

    def _extract_connected_chains(self, swings: tuple[Swing, ...]) -> tuple[tuple[Swing, ...], ...]:
        """Split swings into contiguous chains while preserving order."""

        chains: list[tuple[Swing, ...]] = []
        current_chain: list[Swing] = [swings[0]]

        for current in swings[1:]:
            previous = current_chain[-1]
            if _swings_are_connected(previous, current):
                current_chain.append(current)
                continue

            chains.append(tuple(current_chain))
            current_chain = [current]

        chains.append(tuple(current_chain))
        return tuple(chains)


def _sliding_windows(
    chain: tuple[Swing, ...],
    minimum_length: int,
) -> tuple[tuple[Swing, ...], ...]:
    """Return all contiguous windows with at least minimum_length swings."""

    windows: list[tuple[Swing, ...]] = []
    chain_length = len(chain)

    if chain_length < minimum_length:
        return ()

    for start_index in range(chain_length):
        windows.extend(
            chain[start_index:end_index]
            for end_index in range(start_index + minimum_length, chain_length + 1)
        )

    return tuple(windows)


def _swings_are_connected(previous: Swing, current: Swing) -> bool:
    """Return True when two swings form a contiguous chain step."""

    return (
        previous.end_pivot.id == current.start_pivot.id
        and previous.end_timestamp <= current.start_timestamp
        and previous.symbol == current.symbol
        and previous.timeframe == current.timeframe
    )


def _deterministic_wave_id(sequence_key: tuple[str, ...]) -> EntityId:
    """Derive a stable candidate wave identifier from swing IDs."""

    raw_key = ",".join(sequence_key)
    return EntityId(value=uuid5(NAMESPACE_URL, f"elliottwaver-wave:{raw_key}"))
