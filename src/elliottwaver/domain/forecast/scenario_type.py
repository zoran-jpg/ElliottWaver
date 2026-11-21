"""Forecast scenario classifications."""

from enum import StrEnum


class ScenarioType(StrEnum):
    """Classification of a deterministic forecast scenario."""

    PRIMARY = "primary"
    ALTERNATIVE = "alternative"
    INVALIDATED = "invalidated"
