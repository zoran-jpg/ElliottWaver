from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import (
    Candle,
    CandleTemporalSemantics,
    ConfirmationTimestampStatus,
    Price,
)


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 28, hour, minute, tzinfo=UTC)


def _semantic(
    *,
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
    available_at: datetime | None = None,
    is_closed: bool | None = None,
) -> CandleTemporalSemantics:
    return CandleTemporalSemantics(
        opened_at=opened_at or _utc(10),
        closed_at=closed_at,
        available_at=available_at,
        is_closed=is_closed,
    )


def test_closed_candle_with_known_availability_can_be_confirmed() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=_utc(11, 5)) is ConfirmationTimestampStatus.CONFIRMED


def test_unknown_close_time_remains_unknown() -> None:
    semantics = _semantic(
        closed_at=None,
        available_at=_utc(11, 5),
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=_utc(12)) is ConfirmationTimestampStatus.UNKNOWN


def test_unknown_availability_time_remains_unknown() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=None,
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=_utc(12)) is ConfirmationTimestampStatus.UNKNOWN


def test_open_candle_is_pending() -> None:
    semantics = _semantic(
        closed_at=None,
        available_at=None,
        is_closed=False,
    )

    assert semantics.confirmation_status(as_of=_utc(12)) is ConfirmationTimestampStatus.PENDING


def test_conflicting_closed_flag_with_close_time_is_rejected() -> None:
    with pytest.raises(DomainError, match="closed_at must be omitted"):
        _semantic(
            closed_at=_utc(11),
            available_at=_utc(11, 5),
            is_closed=False,
        )


def test_invalid_time_order_is_rejected() -> None:
    with pytest.raises(DomainError, match="closed_at must be after opened_at"):
        _semantic(
            opened_at=_utc(10),
            closed_at=_utc(10),
            available_at=_utc(11),
            is_closed=True,
        )


def test_partially_known_but_conflicting_times_are_rejected() -> None:
    with pytest.raises(DomainError, match="available_at must not be before closed_at"):
        _semantic(
            closed_at=_utc(11),
            available_at=_utc(10, 59),
            is_closed=True,
        )


def test_available_at_before_opened_at_is_rejected_even_when_close_time_unknown() -> None:
    with pytest.raises(DomainError, match="available_at must not be before opened_at"):
        _semantic(
            opened_at=_utc(10),
            closed_at=None,
            available_at=_utc(9, 59),
            is_closed=True,
        )


def test_available_at_equal_opened_at_is_allowed_when_close_time_unknown() -> None:
    semantics = _semantic(
        opened_at=_utc(10),
        closed_at=None,
        available_at=_utc(10),
        is_closed=True,
    )

    assert semantics.available_at == _utc(10)
    assert semantics.confirmation_status(as_of=_utc(12)) is ConfirmationTimestampStatus.UNKNOWN


def test_available_at_after_opened_at_is_allowed_when_close_time_unknown() -> None:
    semantics = _semantic(
        opened_at=_utc(10),
        closed_at=None,
        available_at=_utc(10, 1),
        is_closed=True,
    )

    assert semantics.available_at == _utc(10, 1)
    assert semantics.confirmation_status(as_of=_utc(12)) is ConfirmationTimestampStatus.UNKNOWN


def test_non_utc_timepoints_are_rejected() -> None:
    utc_plus_one = timezone(timedelta(hours=1))
    with pytest.raises(DomainError, match="timezone-aware UTC"):
        _semantic(
            opened_at=datetime(2026, 11, 28, 10, 0, tzinfo=utc_plus_one),
            closed_at=_utc(11),
            available_at=_utc(11, 5),
            is_closed=True,
        )


def test_naive_timepoints_are_rejected() -> None:
    with pytest.raises(DomainError, match="timezone-aware UTC"):
        _semantic(
            opened_at=datetime(2026, 11, 28, 10, 0),  # noqa: DTZ001
            closed_at=_utc(11),
            available_at=_utc(11, 5),
            is_closed=True,
        )


def test_available_at_equal_as_of_is_confirmed() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=_utc(11, 5)) is ConfirmationTimestampStatus.CONFIRMED


def test_available_at_after_as_of_is_pending() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=_utc(11, 4)) is ConfirmationTimestampStatus.PENDING


def test_available_at_before_as_of_is_confirmed() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=_utc(12)) is ConfirmationTimestampStatus.CONFIRMED


def test_available_at_equal_closed_at_is_allowed() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11),
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=_utc(11)) is ConfirmationTimestampStatus.CONFIRMED


def test_invalid_as_of_timestamp_is_rejected() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    with pytest.raises(DomainError, match="as_of must be timezone-aware UTC"):
        semantics.confirmation_status(as_of=datetime(2026, 11, 28, 12, 0))  # noqa: DTZ001


def test_non_utc_as_of_is_rejected_with_complete_metadata() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    with pytest.raises(DomainError, match="as_of must be timezone-aware UTC"):
        semantics.confirmation_status(
            as_of=datetime(2026, 11, 28, 12, 0, tzinfo=timezone(timedelta(hours=1)))
        )


def test_missing_metadata_never_implies_confirmation() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=None) is ConfirmationTimestampStatus.UNKNOWN


def test_as_of_none_with_incomplete_metadata_remains_unknown() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=None,
        is_closed=True,
    )

    assert semantics.confirmation_status(as_of=None) is ConfirmationTimestampStatus.UNKNOWN


def test_open_candle_with_known_availability_remains_pending() -> None:
    semantics = _semantic(
        closed_at=None,
        available_at=_utc(10, 30),
        is_closed=False,
    )

    assert semantics.confirmation_status(as_of=_utc(10, 30)) is ConfirmationTimestampStatus.PENDING
    assert semantics.confirmation_status(as_of=_utc(15)) is ConfirmationTimestampStatus.PENDING


def test_open_candle_with_as_of_none_remains_pending() -> None:
    semantics = _semantic(
        closed_at=None,
        available_at=_utc(10, 30),
        is_closed=False,
    )

    assert semantics.confirmation_status(as_of=None) is ConfirmationTimestampStatus.PENDING


def test_invalid_as_of_is_not_validated_when_metadata_is_incomplete() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=None,
        is_closed=True,
    )

    with pytest.raises(DomainError, match="as_of must be timezone-aware UTC"):
        semantics.confirmation_status(as_of=datetime(2026, 11, 28, 12, 0))  # noqa: DTZ001


def test_non_utc_as_of_is_rejected_with_incomplete_metadata() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=None,
        is_closed=True,
    )

    with pytest.raises(DomainError, match="as_of must be timezone-aware UTC"):
        semantics.confirmation_status(
            as_of=datetime(2026, 11, 28, 12, 0, tzinfo=timezone(timedelta(hours=1)))
        )


def test_invalid_as_of_is_not_validated_for_open_candle_pending_path() -> None:
    semantics = _semantic(
        closed_at=None,
        available_at=_utc(10, 30),
        is_closed=False,
    )

    with pytest.raises(DomainError, match="as_of must be timezone-aware UTC"):
        semantics.confirmation_status(as_of=datetime(2026, 11, 28, 12, 0))  # noqa: DTZ001


def test_non_utc_as_of_is_rejected_for_open_candle_pending_path() -> None:
    semantics = _semantic(
        closed_at=None,
        available_at=_utc(10, 30),
        is_closed=False,
    )

    with pytest.raises(DomainError, match="as_of must be timezone-aware UTC"):
        semantics.confirmation_status(
            as_of=datetime(2026, 11, 28, 12, 0, tzinfo=timezone(timedelta(hours=1)))
        )


def test_semantics_value_object_is_immutable() -> None:
    semantics = _semantic(
        closed_at=_utc(11),
        available_at=_utc(11, 5),
        is_closed=True,
    )

    with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
        semantics.available_at = _utc(11, 6)  # type: ignore[misc]


def test_existing_candle_construction_remains_compatible() -> None:
    candle = Candle(
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        opened_at=_utc(10),
        open=Price.parse(Decimal("100")),
        high=Price.parse(Decimal("101")),
        low=Price.parse(Decimal("99")),
        close=Price.parse(Decimal("100.5")),
        volume=Decimal("1000"),
    )

    assert candle.opened_at == _utc(10)
