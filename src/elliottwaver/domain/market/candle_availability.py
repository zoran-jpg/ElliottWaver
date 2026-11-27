"""Shared temporal availability semantics for market candles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from elliottwaver.core.shared.errors import DomainError

_UTC_OFFSET = UTC.utcoffset(None)


class ConfirmationTimestampStatus(StrEnum):
    """Temporal confirmation state resolved against an explicit as-of timestamp."""

    UNKNOWN = "unknown"
    CONFIRMED = "confirmed"
    PENDING = "pending"


@dataclass(frozen=True, slots=True)
class CandleTemporalSemantics:
    """Immutable temporal availability metadata for one candle."""

    opened_at: datetime
    closed_at: datetime | None = None
    available_at: datetime | None = None
    is_closed: bool | None = None

    def __post_init__(self) -> None:
        _validate_utc_datetime(self.opened_at, "opened_at")

        if self.closed_at is not None:
            _validate_utc_datetime(self.closed_at, "closed_at")
            if self.closed_at <= self.opened_at:
                message = "closed_at must be after opened_at"
                raise DomainError(message)

        if self.available_at is not None:
            _validate_utc_datetime(self.available_at, "available_at")
            if self.available_at < self.opened_at:
                message = "available_at must not be before opened_at"
                raise DomainError(message)

        if self.is_closed is False and self.closed_at is not None:
            message = "closed_at must be omitted when is_closed is False"
            raise DomainError(message)

        if (
            self.closed_at is not None
            and self.available_at is not None
            and self.available_at < self.closed_at
        ):
            message = "available_at must not be before closed_at"
            raise DomainError(message)

    def confirmation_status(self, *, as_of: datetime | None) -> ConfirmationTimestampStatus:
        """Resolve temporal confirmation against an explicit as-of timestamp."""

        if as_of is not None:
            _validate_utc_datetime(as_of, "as_of")

        if self.is_closed is False:
            return ConfirmationTimestampStatus.PENDING

        if (
            self.is_closed is not True
            or self.closed_at is None
            or self.available_at is None
            or as_of is None
        ):
            return ConfirmationTimestampStatus.UNKNOWN

        if self.available_at <= as_of:
            return ConfirmationTimestampStatus.CONFIRMED
        return ConfirmationTimestampStatus.PENDING


def _validate_utc_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != _UTC_OFFSET:
        message = f"{field_name} must be timezone-aware UTC"
        raise DomainError(message)
