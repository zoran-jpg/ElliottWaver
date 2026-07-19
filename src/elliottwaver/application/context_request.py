"""Context use-case request contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.domain.confluence import MultiTimeframeConfluenceResult
    from elliottwaver.domain.multi_timeframe import Timeframe
    from elliottwaver.domain.selection import SelectedWaveCandidate
    from elliottwaver.domain.trend_hierarchy import TrendHierarchy


@dataclass(frozen=True, slots=True)
class ContextRequest:
    """Input contract for context creation."""

    selected_wave: SelectedWaveCandidate | None
    trend_hierarchy: TrendHierarchy | None = None
    confluence_result: MultiTimeframeConfluenceResult | None = None
    trend_level: Timeframe | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if self.selected_wave is None:
            message = "selected_wave must not be None"
            raise DomainError(message)

        normalized_correlation_id = self.correlation_id
        if normalized_correlation_id is not None:
            normalized_correlation_id = normalized_correlation_id.strip()
            if not normalized_correlation_id:
                message = "correlation_id must not be empty"
                raise DomainError(message)
            object.__setattr__(self, "correlation_id", normalized_correlation_id)
