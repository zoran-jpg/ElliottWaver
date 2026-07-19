"""Completion-level classification for Elliott context maturity."""

from enum import StrEnum


class CompletionLevel(StrEnum):
    """Stable maturity stages for contextual wave interpretation."""

    EARLY = "early"
    DEVELOPING = "developing"
    MATURE = "mature"
    COMPLETED = "completed"
