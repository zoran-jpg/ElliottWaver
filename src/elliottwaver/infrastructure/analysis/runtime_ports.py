"""Infrastructure adapters for analysis runtime ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from elliottwaver.application import AnalysisClock, AnalysisIdProvider
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.core.time.clock import utc_now

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class SystemAnalysisClock(AnalysisClock):
    """UTC wall-clock adapter for analysis orchestration."""

    def now(self) -> datetime:
        """Return the current UTC datetime."""

        return utc_now()


@dataclass(frozen=True, slots=True)
class UuidAnalysisIdProvider(AnalysisIdProvider):
    """EntityId generator adapter for analysis orchestration."""

    def next_analysis_id(self) -> EntityId:
        """Return a new non-nil analysis identifier."""

        return EntityId.new()
