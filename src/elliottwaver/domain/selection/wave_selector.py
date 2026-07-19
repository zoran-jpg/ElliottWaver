"""Wave candidate selection engine and pluggable selection policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from elliottwaver.domain.scoring import ScoredWaveCandidate, ScoringResult

if TYPE_CHECKING:
    from elliottwaver.domain.detection import WaveCandidate
    from elliottwaver.domain.scoring import WaveScore


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")

REASON_HIGHEST_SCORE = "highest_score"
REASON_MINIMUM_SCORE_REACHED = "minimum_score_reached"
REASON_SUFFICIENT_SCORE_GAP = "sufficient_score_gap"


@dataclass(frozen=True, slots=True)
class SelectionConfig:
    """Centralized configuration values used by selection policies."""

    minimum_score_percent: Decimal = Decimal("70")
    minimum_score_gap_percent: Decimal = Decimal("5")
    maximum_selected_candidates: int = 1

    def __post_init__(self) -> None:
        if not (_ZERO <= self.minimum_score_percent <= _HUNDRED):
            message = "minimum_score_percent must be within [0, 100]"
            raise ValueError(message)

        if not (_ZERO <= self.minimum_score_gap_percent <= _HUNDRED):
            message = "minimum_score_gap_percent must be within [0, 100]"
            raise ValueError(message)

        if self.maximum_selected_candidates < 1:
            message = "maximum_selected_candidates must be > 0"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class SelectionReason:
    """Structured explanation for a selected candidate."""

    policy_name: str
    reason_code: str
    message: str
    metrics: tuple[tuple[str, Decimal], ...] = ()

    def __post_init__(self) -> None:
        if not self.policy_name.strip():
            message = "policy_name must not be empty"
            raise ValueError(message)

        if not self.reason_code.strip():
            message = "reason_code must not be empty"
            raise ValueError(message)

        if not self.message.strip():
            message = "message must not be empty"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class SelectedWaveCandidate:
    """A scored candidate selected by a policy with associated reasons."""

    scored_candidate: ScoredWaveCandidate
    reasons: tuple[SelectionReason, ...]
    rank: int

    def __post_init__(self) -> None:
        if self.rank < 1:
            message = "rank must be >= 1"
            raise ValueError(message)

        if not self.reasons:
            message = "reasons must not be empty"
            raise ValueError(message)

    @property
    def wave_candidate(self) -> WaveCandidate:
        """Return the underlying wave candidate."""

        return self.scored_candidate.candidate

    @property
    def wave_score(self) -> WaveScore:
        """Return the already computed wave score."""

        return self.scored_candidate.score


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """Selection output for a specific policy and scored input set."""

    selected_candidates: tuple[SelectedWaveCandidate, ...]
    policy_name: str
    considered_candidates: int

    def __post_init__(self) -> None:
        if not self.policy_name.strip():
            message = "policy_name must not be empty"
            raise ValueError(message)

        if self.considered_candidates < 0:
            message = "considered_candidates must be >= 0"
            raise ValueError(message)

        expected_rank = 1
        seen_wave_ids: set[str] = set()

        for selected in self.selected_candidates:
            if selected.rank != expected_rank:
                message = "selected candidate ranks must be consecutive starting at 1"
                raise ValueError(message)

            wave_id = str(selected.wave_candidate.wave.id)
            if wave_id in seen_wave_ids:
                message = "selected_candidates must not contain duplicates"
                raise ValueError(message)

            seen_wave_ids.add(wave_id)
            expected_rank += 1

    @property
    def has_selection(self) -> bool:
        """Return True when at least one candidate was selected."""

        return bool(self.selected_candidates)

    @property
    def is_empty(self) -> bool:
        """Return True when no candidate was selected."""

        return not self.selected_candidates

    @property
    def selected_count(self) -> int:
        """Return the number of selected candidates."""

        return len(self.selected_candidates)

    @property
    def primary_candidate(self) -> SelectedWaveCandidate | None:
        """Return the first selected candidate or None."""

        if not self.selected_candidates:
            return None
        return self.selected_candidates[0]


@runtime_checkable
class SelectionPolicy(Protocol):
    """Pluggable deterministic selection strategy."""

    @property
    def name(self) -> str:
        """Return policy identifier."""

    def select(
        self,
        scored_candidates: ScoringResult | tuple[ScoredWaveCandidate, ...],
        config: SelectionConfig,
    ) -> tuple[SelectedWaveCandidate, ...]:
        """Select candidates from a scored input without re-scoring."""


@dataclass(frozen=True, slots=True)
class TopScoreSelectionPolicy:
    """Select the highest-ranked scored candidate."""

    name: str = "top_score"

    def select(
        self,
        scored_candidates: ScoringResult | tuple[ScoredWaveCandidate, ...],
        config: SelectionConfig,
    ) -> tuple[SelectedWaveCandidate, ...]:
        candidates = _as_scored_candidates(scored_candidates)

        if not candidates:
            return ()

        reason = SelectionReason(
            policy_name=self.name,
            reason_code=REASON_HIGHEST_SCORE,
            message="Selected highest scored candidate",
            metrics=(("score_percent", candidates[0].score.percentage),),
        )

        return (
            SelectedWaveCandidate(
                scored_candidate=candidates[0],
                reasons=(reason,),
                rank=1,
            ),
        )[: config.maximum_selected_candidates]


@dataclass(frozen=True, slots=True)
class MinimumScoreSelectionPolicy:
    """Select all candidates that meet or exceed a score threshold."""

    name: str = "minimum_score"

    def select(
        self,
        scored_candidates: ScoringResult | tuple[ScoredWaveCandidate, ...],
        config: SelectionConfig,
    ) -> tuple[SelectedWaveCandidate, ...]:
        candidates = _as_scored_candidates(scored_candidates)

        selected: list[SelectedWaveCandidate] = []
        rank = 1

        for candidate in candidates:
            if candidate.score.percentage < config.minimum_score_percent:
                continue

            reason = SelectionReason(
                policy_name=self.name,
                reason_code=REASON_MINIMUM_SCORE_REACHED,
                message="Candidate meets minimum score threshold",
                metrics=(
                    ("score_percent", candidate.score.percentage),
                    ("minimum_score_percent", config.minimum_score_percent),
                ),
            )
            selected.append(
                SelectedWaveCandidate(
                    scored_candidate=candidate,
                    reasons=(reason,),
                    rank=rank,
                )
            )
            rank += 1

            if len(selected) >= config.maximum_selected_candidates:
                break

        return tuple(selected)


@dataclass(frozen=True, slots=True)
class ScoreGapSelectionPolicy:
    """Select top candidate only if score gap to runner-up is sufficient."""

    name: str = "score_gap"

    def select(
        self,
        scored_candidates: ScoringResult | tuple[ScoredWaveCandidate, ...],
        config: SelectionConfig,
    ) -> tuple[SelectedWaveCandidate, ...]:
        candidates = _as_scored_candidates(scored_candidates)

        if not candidates:
            return ()

        if len(candidates) == 1:
            reason = SelectionReason(
                policy_name=self.name,
                reason_code=REASON_HIGHEST_SCORE,
                message="Single candidate available; selected top score",
                metrics=(("score_percent", candidates[0].score.percentage),),
            )
            return (
                SelectedWaveCandidate(
                    scored_candidate=candidates[0],
                    reasons=(reason,),
                    rank=1,
                ),
            )[: config.maximum_selected_candidates]

        best = candidates[0]
        next_best = candidates[1]
        observed_gap = best.score.percentage - next_best.score.percentage

        if observed_gap < config.minimum_score_gap_percent:
            return ()

        reason = SelectionReason(
            policy_name=self.name,
            reason_code=REASON_SUFFICIENT_SCORE_GAP,
            message="Top candidate has sufficient score gap",
            metrics=(
                ("best_score_percent", best.score.percentage),
                ("next_score_percent", next_best.score.percentage),
                ("observed_gap_percent", observed_gap),
                ("minimum_score_gap_percent", config.minimum_score_gap_percent),
            ),
        )

        return (
            SelectedWaveCandidate(
                scored_candidate=best,
                reasons=(reason,),
                rank=1,
            ),
        )[: config.maximum_selected_candidates]


@dataclass(frozen=True, slots=True)
class WaveSelector:
    """Apply a configurable selection policy to scored candidates."""

    policy: SelectionPolicy = field(default_factory=TopScoreSelectionPolicy)
    config: SelectionConfig = field(default_factory=SelectionConfig)

    def select(self, scoring_result: ScoringResult) -> SelectionResult:
        """Select candidates from a scored result using configured policy."""

        selected = self.policy.select(scoring_result, self.config)
        limited = selected[: self.config.maximum_selected_candidates]

        return SelectionResult(
            selected_candidates=limited,
            policy_name=self.policy.name,
            considered_candidates=len(scoring_result.scored_candidates),
        )


def _as_scored_candidates(
    scored_candidates: ScoringResult | tuple[ScoredWaveCandidate, ...],
) -> tuple[ScoredWaveCandidate, ...]:
    """Normalize policy input to a tuple of scored candidates."""

    if isinstance(scored_candidates, ScoringResult):
        return scored_candidates.scored_candidates
    return scored_candidates
