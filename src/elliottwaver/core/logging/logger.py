"""Logging helpers."""

from typing import TYPE_CHECKING, cast

import structlog

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


def get_logger() -> "BoundLogger":
    """Return the project logger."""

    return cast("BoundLogger", structlog.get_logger("elliottwaver"))
