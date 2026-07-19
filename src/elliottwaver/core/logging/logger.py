"""Logging helpers."""

from typing import cast

import structlog
from structlog.stdlib import BoundLogger


def get_logger() -> BoundLogger:
    """Return the project logger."""

    return cast(BoundLogger, structlog.get_logger("elliottwaver"))
