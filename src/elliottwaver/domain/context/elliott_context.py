"""Immutable Elliott context aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.domain.context.completion_level import CompletionLevel
    from elliottwaver.domain.context.context_strength import ContextStrength
    from elliottwaver.domain.market.wave import WaveDegree
    from elliottwaver.domain.multi_timeframe import Timeframe
    from elliottwaver.domain.selection import SelectedWaveCandidate

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class ElliottContext:
    """Structured context derived from already computed analysis artifacts."""

    selected_wave: SelectedWaveCandidate
    trend_alignment: bool | None
    completion_level: CompletionLevel
    context_strength: ContextStrength
    confidence: Decimal
    confluence_score: Decimal
    trend_level: Timeframe | None
    wave_degree: WaveDegree
    structural_quality: Decimal

    def __post_init__(self) -> None:
        _validate_percent(self.confidence, "confidence")
        _validate_percent(self.confluence_score, "confluence_score")
        _validate_percent(self.structural_quality, "structural_quality")

        if self.wave_degree is not self.selected_wave.wave_candidate.wave.degree:
            message = "wave_degree must match selected_wave.wave_candidate.wave.degree"
            raise DomainError(message)


def _validate_percent(value: Decimal, field_name: str) -> None:
    if not value.is_finite():
        message = f"{field_name} must be finite"
        raise DomainError(message)
    if value < _ZERO or value > _HUNDRED:
        message = f"{field_name} must be within [0, 100]"
        raise DomainError(message)
