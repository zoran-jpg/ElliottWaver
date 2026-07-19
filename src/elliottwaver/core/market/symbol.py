"""Financial instrument symbol."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SYMBOL_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9._-]{0,31}")


@dataclass(frozen=True, slots=True)
class Symbol:
    """Normalized financial instrument symbol."""

    value: str

    def __post_init__(self) -> None:
        """Normalize and validate the symbol."""

        normalized_value = self.value.strip().upper()

        if not _SYMBOL_PATTERN.fullmatch(normalized_value):
            message = f"Invalid market symbol: {self.value!r}"
            raise ValueError(message)

        object.__setattr__(self, "value", normalized_value)

    def __str__(self) -> str:
        """Return the normalized symbol value."""

        return self.value
