from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.context import CompletionLevel, ContextStrength, ElliottContext
from elliottwaver.domain.market.wave import WaveDegree
from elliottwaver.domain.multi_timeframe import Timeframe

from .helpers import make_selected_wave_candidate


def test_elliott_context_is_immutable_and_valid() -> None:
    selected = make_selected_wave_candidate()

    context = ElliottContext(
        selected_wave=selected,
        trend_alignment=True,
        completion_level=CompletionLevel.MATURE,
        context_strength=ContextStrength.STRONG,
        confidence=Decimal("78"),
        confluence_score=Decimal("66"),
        trend_level=Timeframe.parse("D1"),
        wave_degree=selected.wave_candidate.wave.degree,
        structural_quality=Decimal("88"),
    )

    assert context.wave_degree is WaveDegree.PRIMARY
    assert context.trend_alignment is True

    with pytest.raises(FrozenInstanceError):
        context.__setattr__("confidence", Decimal("1"))


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("confidence", Decimal("101")),
        ("confluence_score", Decimal("-1")),
        ("structural_quality", Decimal("1000")),
    ],
)
def test_elliott_context_rejects_invalid_percent_values(
    field_name: str,
    field_value: Decimal,
) -> None:
    selected = make_selected_wave_candidate()

    kwargs: dict[str, Any] = {
        "selected_wave": selected,
        "trend_alignment": True,
        "completion_level": CompletionLevel.MATURE,
        "context_strength": ContextStrength.STRONG,
        "confidence": Decimal("78"),
        "confluence_score": Decimal("66"),
        "trend_level": Timeframe.parse("D1"),
        "wave_degree": selected.wave_candidate.wave.degree,
        "structural_quality": Decimal("88"),
    }
    kwargs[field_name] = field_value

    with pytest.raises(DomainError, match=r"must be within \[0, 100\]"):
        ElliottContext(**kwargs)


def test_elliott_context_rejects_wave_degree_mismatch() -> None:
    selected = make_selected_wave_candidate()

    with pytest.raises(DomainError, match="wave_degree must match"):
        ElliottContext(
            selected_wave=selected,
            trend_alignment=None,
            completion_level=CompletionLevel.EARLY,
            context_strength=ContextStrength.WEAK,
            confidence=Decimal("10"),
            confluence_score=Decimal("0"),
            trend_level=None,
            wave_degree=WaveDegree.SECONDARY,
            structural_quality=Decimal("40"),
        )
