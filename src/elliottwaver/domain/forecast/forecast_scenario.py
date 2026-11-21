"""Immutable Elliott forecast scenario."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.forecast.scenario_type import ScenarioType

if TYPE_CHECKING:
    from elliottwaver.domain.forecast.projection_target import ProjectionTarget


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class ForecastScenario:
    """A deterministic and explainable Elliott continuation scenario."""

    scenario_type: ScenarioType
    expected_next_wave: str
    confidence: Decimal
    projection_targets: tuple[ProjectionTarget, ...]
    reasoning: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate forecast-scenario invariants."""

        if not self.expected_next_wave.strip():
            message = "expected_next_wave must not be empty"
            raise DomainError(message)

        _validate_percent(self.confidence, "confidence")
        _validate_reasoning(self.reasoning)
        _validate_projection_targets(
            scenario_type=self.scenario_type,
            projection_targets=self.projection_targets,
        )

    @property
    def is_primary(self) -> bool:
        """Return whether this is the primary forecast scenario."""

        return self.scenario_type is ScenarioType.PRIMARY

    @property
    def is_alternative(self) -> bool:
        """Return whether this is an alternative forecast scenario."""

        return self.scenario_type is ScenarioType.ALTERNATIVE

    @property
    def is_invalidated(self) -> bool:
        """Return whether this scenario has been invalidated."""

        return self.scenario_type is ScenarioType.INVALIDATED


def _validate_reasoning(reasoning: tuple[str, ...]) -> None:
    if not reasoning:
        message = "reasoning must not be empty"
        raise DomainError(message)

    if any(not reason.strip() for reason in reasoning):
        message = "reasoning entries must not be empty"
        raise DomainError(message)

    if len(set(reasoning)) != len(reasoning):
        message = "reasoning entries must be unique"
        raise DomainError(message)


def _validate_projection_targets(
    *,
    scenario_type: ScenarioType,
    projection_targets: tuple[ProjectionTarget, ...],
) -> None:
    if scenario_type is not ScenarioType.INVALIDATED and not projection_targets:
        message = "active forecast scenarios must contain at least one projection target"
        raise DomainError(message)

    priorities = tuple(target.priority for target in projection_targets)

    if len(set(priorities)) != len(priorities):
        message = "projection target priorities must be unique"
        raise DomainError(message)

    expected_priorities = tuple(range(1, len(projection_targets) + 1))

    if tuple(sorted(priorities)) != expected_priorities:
        message = "projection target priorities must be consecutive starting at 1"
        raise DomainError(message)


def _validate_percent(value: Decimal, field_name: str) -> None:
    if not value.is_finite():
        message = f"{field_name} must be finite"
        raise DomainError(message)

    if value < _ZERO or value > _HUNDRED:
        message = f"{field_name} must be within [0, 100]"
        raise DomainError(message)
