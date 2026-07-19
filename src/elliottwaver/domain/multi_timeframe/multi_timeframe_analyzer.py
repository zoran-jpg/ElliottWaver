"""Multi-timeframe orchestration over existing selection results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import total_ordering
from typing import TYPE_CHECKING, ClassVar

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.core.market import Symbol
    from elliottwaver.domain.selection import SelectedWaveCandidate, SelectionResult


@total_ordering
@dataclass(frozen=True, slots=True)
class Timeframe:
    """Immutable timeframe value object with hierarchy semantics."""

    value: str

    _ORDERED_VALUES: ClassVar[tuple[str, ...]] = (
        "MN1",
        "W1",
        "D1",
        "H4",
        "H1",
        "M30",
        "M15",
        "M5",
        "M1",
    )

    def __post_init__(self) -> None:
        normalized_value = self.value.strip().upper()

        if normalized_value not in self._ORDERED_VALUES:
            message = f"Unsupported timeframe: {self.value!r}"
            raise DomainError(message)

        object.__setattr__(self, "value", normalized_value)

    @classmethod
    def parse(cls, value: str) -> Timeframe:
        """Parse and validate a timeframe string."""

        return cls(value=value)

    @property
    def hierarchy_index(self) -> int:
        """Return hierarchy index, where lower index means higher timeframe."""

        return self._ORDERED_VALUES.index(self.value)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Timeframe):
            return NotImplemented

        return self.hierarchy_index < other.hierarchy_index

    def __str__(self) -> str:
        """Return normalized timeframe identifier."""

        return self.value


@dataclass(frozen=True, slots=True)
class TimeframeAnalysis:
    """Selection analysis context for one timeframe."""

    timeframe: Timeframe
    selection_result: SelectionResult
    analysed_at: datetime
    symbol: Symbol
    analysed_candidates_count: int

    def __post_init__(self) -> None:
        if self.analysed_at.tzinfo is None or self.analysed_at.utcoffset() != UTC.utcoffset(None):
            message = "analysed_at must be timezone-aware UTC"
            raise DomainError(message)

        if self.analysed_candidates_count < 0:
            message = "analysed_candidates_count must be >= 0"
            raise DomainError(message)

        if self.analysed_candidates_count != self.selection_result.considered_candidates:
            message = "analysed_candidates_count must equal selection_result.considered_candidates"
            raise DomainError(message)

    @property
    def has_selection(self) -> bool:
        """Return whether this timeframe has selected candidates."""

        return self.selection_result.has_selection

    @property
    def primary_candidate(self) -> SelectedWaveCandidate | None:
        """Return the selected primary candidate if present."""

        return self.selection_result.primary_candidate

    @property
    def selected_count(self) -> int:
        """Return number of selected candidates for the timeframe."""

        return self.selection_result.selected_count


@dataclass(frozen=True, slots=True)
class MultiTimeframeAnalysis:
    """Immutable ordered collection of per-timeframe analyses."""

    analyses: tuple[TimeframeAnalysis, ...] = ()

    def __post_init__(self) -> None:
        sorted_analyses = tuple(
            sorted(self.analyses, key=lambda item: item.timeframe.hierarchy_index)
        )
        seen: set[Timeframe] = set()

        for analysis in sorted_analyses:
            if analysis.timeframe in seen:
                message = "analyses must not contain duplicate timeframes"
                raise DomainError(message)
            seen.add(analysis.timeframe)

        object.__setattr__(self, "analyses", sorted_analyses)

    @property
    def highest_timeframe(self) -> Timeframe | None:
        """Return highest timeframe in hierarchy order."""

        if not self.analyses:
            return None
        return self.analyses[0].timeframe

    @property
    def lowest_timeframe(self) -> Timeframe | None:
        """Return lowest timeframe in hierarchy order."""

        if not self.analyses:
            return None
        return self.analyses[-1].timeframe

    @property
    def analysed_timeframes(self) -> tuple[Timeframe, ...]:
        """Return all analysed timeframes in stable hierarchy order."""

        return tuple(analysis.timeframe for analysis in self.analyses)

    @property
    def has_results(self) -> bool:
        """Return whether at least one timeframe analysis exists."""

        return bool(self.analyses)


@dataclass(frozen=True, slots=True)
class MultiTimeframeAnalyzer:
    """Deterministic orchestrator for multi-timeframe selection results."""

    def analyze(
        self,
        selections_by_timeframe: tuple[tuple[Timeframe, SelectionResult], ...],
        *,
        symbol: Symbol,
        analysed_at: datetime,
    ) -> MultiTimeframeAnalysis:
        """Build a multi-timeframe analysis without rescoring or redetection."""

        analyses = tuple(
            TimeframeAnalysis(
                timeframe=timeframe,
                selection_result=selection_result,
                analysed_at=analysed_at,
                symbol=symbol,
                analysed_candidates_count=selection_result.considered_candidates,
            )
            for timeframe, selection_result in selections_by_timeframe
        )

        return MultiTimeframeAnalysis(analyses=analyses)
