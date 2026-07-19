"""Base class for immutable value objects."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Marker base class for immutable, equality-based domain values."""
