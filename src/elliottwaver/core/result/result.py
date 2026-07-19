"""Generic Result type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Success[T]:
    value: T


@dataclass(frozen=True, slots=True)
class Failure[E]:
    error: E


type Result[T, E] = Success[T] | Failure[E]
