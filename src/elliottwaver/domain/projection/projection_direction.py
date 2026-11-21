"""Explicit projection direction values."""

from enum import StrEnum


class ProjectionDirection(StrEnum):
    """Direction for forward or reverse price projection."""

    UP = "up"
    DOWN = "down"
