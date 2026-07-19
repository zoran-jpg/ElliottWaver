"""Strength classification for computed Elliott context."""

from enum import StrEnum


class ContextStrength(StrEnum):
    """Stable qualitative strength buckets."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"
