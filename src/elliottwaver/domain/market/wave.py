"""Wave domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from elliottwaver.core.shared.entity import Entity
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from elliottwaver.core.market import Symbol, Timeframe
    from elliottwaver.domain.market.swing import Swing, SwingDirection


class WaveType(StrEnum):
    """Classification of an Elliott wave."""

    IMPULSE = "impulse"
    CORRECTIVE = "corrective"


class WaveDegree(StrEnum):
    """Relative degree of a wave."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    INTERMEDIATE = "intermediate"


@dataclass(frozen=True, eq=False, slots=True)
class Wave(Entity[EntityId]):
    """A sequence of connected swings forming a wave."""

    id: EntityId
    wave_type: WaveType
    degree: WaveDegree
    swings: tuple[Swing, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate wave invariants at construction."""

        swings = tuple(self.swings)

        if not swings:
            message = "Wave must contain at least one swing"
            raise DomainError(message)

        if len(set(swings)) != len(swings):
            message = "Wave swings must be unique"
            raise DomainError(message)

        if self.wave_type not in WaveType:
            message = "wave_type must be a WaveType"
            raise DomainError(message)

        if self.degree not in WaveDegree:
            message = "degree must be a WaveDegree"
            raise DomainError(message)

        if swings[0].symbol != swings[-1].symbol:
            message = "Wave swings must share the same symbol"
            raise DomainError(message)

        if swings[0].timeframe != swings[-1].timeframe:
            message = "Wave swings must share the same timeframe"
            raise DomainError(message)

        for index, current in enumerate(swings[1:], start=1):
            previous = swings[index - 1]

            if (
                previous.end_timestamp > current.start_timestamp
                and previous.end_pivot.id != current.start_pivot.id
            ):
                message = "Wave swings must be chronological"
                raise DomainError(message)

            if previous.end_pivot.id != current.start_pivot.id:
                message = "Wave swings must form a connected chain"
                raise DomainError(message)

            if previous.symbol != current.symbol:
                message = "Wave swings must share the same symbol"
                raise DomainError(message)

            if previous.timeframe != current.timeframe:
                message = "Wave swings must share the same timeframe"
                raise DomainError(message)

            if previous.direction == current.direction:
                message = "Wave swings must alternate"
                raise DomainError(message)

    @property
    def symbol(self) -> Symbol:
        """Return the wave symbol."""

        return self.swings[0].symbol

    @property
    def timeframe(self) -> Timeframe:
        """Return the wave timeframe."""

        return self.swings[0].timeframe

    @property
    def start_timestamp(self) -> datetime:
        """Return the start timestamp of the first swing."""

        return self.swings[0].start_timestamp

    @property
    def end_timestamp(self) -> datetime:
        """Return the end timestamp of the last swing."""

        return self.swings[-1].end_timestamp

    @property
    def duration(self) -> timedelta:
        """Return the duration from the first start to the last end."""

        return self.end_timestamp - self.start_timestamp

    @property
    def direction(self) -> SwingDirection:
        """Return the direction of the first swing."""

        return self.swings[0].direction
