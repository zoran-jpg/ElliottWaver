"""Wave-candidate scoring components and scoring engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from functools import total_ordering
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from elliottwaver.domain.detection.wave_detector import WaveCandidate
    from elliottwaver.domain.market.swing import Swing
    from elliottwaver.domain.rules.wave_rules import RuleResult


_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_IMPULSE_MIN_SWINGS = 5


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    """Single weighted scoring contribution."""

    name: str
    weight: Decimal
    value: Decimal
    max_value: Decimal

    def __post_init__(self) -> None:
        if self.weight < _ZERO:
            message = "ScoreComponent weight must be non-negative"
            raise ValueError(message)

        if self.max_value <= _ZERO:
            message = "ScoreComponent max_value must be > 0"
            raise ValueError(message)

        if self.value < _ZERO or self.value > self.max_value:
            message = "ScoreComponent value must be within [0, max_value]"
            raise ValueError(message)

    @property
    def normalized(self) -> Decimal:
        """Return component value as a normalized ratio in [0, 1]."""

        return self.value / self.max_value

    @property
    def weighted_score(self) -> Decimal:
        """Return weighted contribution to the total score."""

        return self.normalized * self.weight


@total_ordering
@dataclass(frozen=True, slots=True)
class WaveScore:
    """Aggregate score for a wave candidate."""

    total_score: Decimal
    components: tuple[ScoreComponent, ...]
    percentage: Decimal

    def __post_init__(self) -> None:
        if self.total_score < _ZERO:
            message = "WaveScore total_score must be non-negative"
            raise ValueError(message)

        if self.percentage < _ZERO or self.percentage > _HUNDRED:
            message = "WaveScore percentage must be within [0, 100]"
            raise ValueError(message)

    @classmethod
    def from_components(cls, components: tuple[ScoreComponent, ...]) -> WaveScore:
        """Build a WaveScore from weighted components."""

        total_weight = sum((component.weight for component in components), _ZERO)
        total_score = sum((component.weighted_score for component in components), _ZERO)

        if total_weight == _ZERO:
            return cls(total_score=_ZERO, components=components, percentage=_ZERO)

        percentage = (total_score / total_weight) * _HUNDRED
        return cls(total_score=total_score, components=components, percentage=percentage)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, WaveScore):
            return NotImplemented
        return self._comparison_key() < other._comparison_key()

    def _comparison_key(self) -> tuple[Decimal, Decimal, tuple[tuple[str, Decimal], ...]]:
        component_key = tuple(
            (component.name, component.weighted_score) for component in self.components
        )
        return (self.percentage, self.total_score, component_key)


@dataclass(frozen=True, slots=True)
class ScoredWaveCandidate:
    """Pair of candidate and its computed score."""

    candidate: WaveCandidate
    score: WaveScore


@dataclass(frozen=True, slots=True)
class ScoringResult:
    """Sorted scored candidates."""

    scored_candidates: tuple[ScoredWaveCandidate, ...] = ()

    def __post_init__(self) -> None:
        sorted_candidates = tuple(
            sorted(
                self.scored_candidates,
                key=lambda item: (
                    -item.score.percentage,
                    -item.score.total_score,
                    str(item.candidate.wave.id),
                ),
            )
        )
        object.__setattr__(self, "scored_candidates", sorted_candidates)

    @property
    def scores(self) -> tuple[WaveScore, ...]:
        """Return sorted scores only."""

        return tuple(item.score for item in self.scored_candidates)


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """Centralized weights for scoring criteria."""

    wave_proportions_weight: Decimal = Decimal("0.30")
    swing_symmetry_weight: Decimal = Decimal("0.20")
    impulse_consistency_weight: Decimal = Decimal("0.30")
    rule_compliance_weight: Decimal = Decimal("0.20")
    fibonacci_extension_weight: Decimal = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class WaveScorer:
    """Scores valid wave candidates using independent criteria."""

    config: ScoringConfig = field(default_factory=ScoringConfig)

    def score(self, candidates: Sequence[WaveCandidate]) -> ScoringResult:
        """Score valid candidates and return sorted scoring result."""

        scored: list[ScoredWaveCandidate] = []
        seen_wave_ids: set[str] = set()

        for candidate in candidates:
            if candidate.is_invalid:
                continue

            wave_id = str(candidate.wave.id)
            if wave_id in seen_wave_ids:
                continue

            components = self._build_components(candidate)
            score = WaveScore.from_components(components)
            scored.append(ScoredWaveCandidate(candidate=candidate, score=score))
            seen_wave_ids.add(wave_id)

        return ScoringResult(scored_candidates=tuple(scored))

    def _build_components(self, candidate: WaveCandidate) -> tuple[ScoreComponent, ...]:
        wave = candidate.wave

        return (
            ScoreComponent(
                name="wave_proportions",
                weight=self.config.wave_proportions_weight,
                value=self._score_wave_proportions(wave.swings),
                max_value=_ONE,
            ),
            ScoreComponent(
                name="swing_symmetry",
                weight=self.config.swing_symmetry_weight,
                value=self._score_swing_symmetry(wave.swings),
                max_value=_ONE,
            ),
            ScoreComponent(
                name="impulse_consistency",
                weight=self.config.impulse_consistency_weight,
                value=self._score_impulse_consistency(wave.swings),
                max_value=_ONE,
            ),
            ScoreComponent(
                name="rule_compliance_bonus",
                weight=self.config.rule_compliance_weight,
                value=self._score_rule_compliance(candidate.rule_result),
                max_value=_ONE,
            ),
            ScoreComponent(
                name="fibonacci_extension_placeholder",
                weight=self.config.fibonacci_extension_weight,
                value=_ZERO,
                max_value=_ONE,
            ),
        )

    def _score_wave_proportions(self, swings: tuple[Swing, ...]) -> Decimal:
        if len(swings) < _IMPULSE_MIN_SWINGS:
            return _ZERO

        lengths = (
            swings[0].absolute_price_change,
            swings[2].absolute_price_change,
            swings[4].absolute_price_change,
        )
        max_length = max(lengths)
        if max_length == _ZERO:
            return _ZERO

        return min(lengths) / max_length

    def _score_swing_symmetry(self, swings: tuple[Swing, ...]) -> Decimal:
        durations = tuple(Decimal(str(swing.duration.total_seconds())) for swing in swings)
        max_duration = max(durations, default=_ZERO)
        if max_duration == _ZERO:
            return _ZERO

        return min(durations) / max_duration

    def _score_impulse_consistency(self, swings: tuple[Swing, ...]) -> Decimal:
        checks = 0
        passed = 0

        for index, swing in enumerate(swings):
            checks += 1
            if swing.absolute_price_change > _ZERO:
                passed += 1

            if index == 0:
                continue

            previous = swings[index - 1]
            checks += 1
            if previous.direction != swing.direction:
                passed += 1

        if checks == 0:
            return _ZERO

        return Decimal(passed) / Decimal(checks)

    def _score_rule_compliance(self, rule_result: RuleResult) -> Decimal:
        return _ONE if rule_result.is_valid else _ZERO
