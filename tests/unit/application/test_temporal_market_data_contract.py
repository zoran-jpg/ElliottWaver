from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from elliottwaver.application.temporal_market_data import TemporalCandleRecord
from elliottwaver.core.market import Symbol, Timeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Candle, CandleTemporalSemantics, Price


def _build_candle(*, opened_at: datetime) -> Candle:
    return Candle(
        symbol=Symbol("EURUSD"),
        timeframe=Timeframe.ONE_HOUR,
        opened_at=opened_at,
        open=Price(Decimal("1.1000")),
        high=Price(Decimal("1.1010")),
        low=Price(Decimal("1.0990")),
        close=Price(Decimal("1.1005")),
        volume=Decimal("10"),
    )


def test_temporal_record_rejects_opened_at_mismatch() -> None:
    candle = _build_candle(opened_at=datetime(2026, 11, 28, 10, 0, tzinfo=UTC))
    semantics = CandleTemporalSemantics(
        opened_at=datetime(2026, 11, 28, 11, 0, tzinfo=UTC),
        closed_at=None,
        available_at=None,
        is_closed=None,
    )

    with pytest.raises(DomainError, match="opened_at must match"):
        TemporalCandleRecord(candle=candle, temporal_semantics=semantics)


def test_from_legacy_candle_creates_obligatory_unknown_semantics() -> None:
    candle = _build_candle(opened_at=datetime(2026, 11, 28, 10, 0, tzinfo=UTC))

    record = TemporalCandleRecord.from_legacy_candle(candle)

    assert record.candle is candle
    assert record.temporal_semantics.opened_at == candle.opened_at
    assert record.temporal_semantics.closed_at is None
    assert record.temporal_semantics.available_at is None
    assert record.temporal_semantics.is_closed is None


def test_temporal_record_is_immutable() -> None:
    candle = _build_candle(opened_at=datetime(2026, 11, 28, 10, 0, tzinfo=UTC))
    record = TemporalCandleRecord.from_legacy_candle(candle)

    with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
        record.temporal_semantics = CandleTemporalSemantics(opened_at=candle.opened_at)  # type: ignore[misc]


def test_temporal_record_rejects_missing_temporal_semantics() -> None:
    candle = _build_candle(opened_at=datetime(2026, 11, 28, 10, 0, tzinfo=UTC))

    with pytest.raises(DomainError, match="Temporal semantics must be provided"):
        TemporalCandleRecord(candle=candle, temporal_semantics=None)  # type: ignore[arg-type]
