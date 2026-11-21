"""Qualitative forecast projection ratings."""

from enum import StrEnum


class ProjectionQuality(StrEnum):
    """Stable quality buckets for an evaluated forecast."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
