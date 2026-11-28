from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import CandleTemporalSemantics, ConfirmationTimestampStatus
from elliottwaver.infrastructure.market_data import csv_market_data_provider as provider_module
from elliottwaver.infrastructure.market_data.csv_market_data_provider import CsvMarketDataProvider

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def test_load_candle_records_legacy_csv_creates_unknown_semantics(tmp_path: Path) -> None:
    csv_path = tmp_path / "legacy.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 11, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    record = records[0]
    assert record.temporal_semantics.opened_at == record.candle.opened_at
    assert record.temporal_semantics.closed_at is None
    assert record.temporal_semantics.available_at is None
    assert record.temporal_semantics.is_closed is None
    assert record.temporal_semantics.confirmation_status(as_of=record.candle.opened_at) is (
        ConfirmationTimestampStatus.UNKNOWN
    )


def test_load_candle_records_parses_temporal_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "temporal.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    semantics = records[0].temporal_semantics
    assert semantics.opened_at == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)
    assert semantics.closed_at == datetime(2026, 11, 28, 10, 59, 59, tzinfo=UTC)
    assert semantics.available_at == datetime(2026, 11, 28, 11, 0, 1, tzinfo=UTC)
    assert semantics.is_closed is True
    assert semantics.confirmation_status(as_of=datetime(2026, 11, 28, 11, 0, 1, tzinfo=UTC)) is (
        ConfirmationTimestampStatus.CONFIRMED
    )


def test_load_candle_records_keeps_empty_optional_temporal_fields_as_none(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty_optional_temporal.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,,,
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    semantics = records[0].temporal_semantics
    assert semantics.closed_at is None
    assert semantics.available_at is None
    assert semantics.is_closed is None


def test_load_candle_records_parses_partially_provided_temporal_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "partial_temporal.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:59:59Z,,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    semantics = records[0].temporal_semantics
    assert semantics.closed_at == datetime(2026, 11, 28, 10, 59, 59, tzinfo=UTC)
    assert semantics.available_at is None
    assert semantics.is_closed is True


def test_load_candle_records_accepts_utc_plus_zero_offset(tmp_path: Path) -> None:
    csv_path = tmp_path / "utc_plus_zero.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00+00:00,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:59:59+00:00,2026-11-28T11:00:01+00:00,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    semantics = records[0].temporal_semantics
    assert semantics.opened_at == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)
    assert semantics.closed_at == datetime(2026, 11, 28, 10, 59, 59, tzinfo=UTC)
    assert semantics.available_at == datetime(2026, 11, 28, 11, 0, 1, tzinfo=UTC)
    assert semantics.is_closed is True


def test_load_candle_records_accepts_trimmed_mixed_case_is_closed_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "trimmed_mixed_case_bool.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1,2026-11-28T10:59:59Z,,"  TrUe  "
        EURUSD,1h,2026-11-28T11:00:00Z,2,3,2,3,1,,,"  fAlSe  "
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert len(records) == 2
    assert records[0].temporal_semantics.is_closed is True
    assert records[1].temporal_semantics.is_closed is False


def test_load_candle_records_rejects_naive_temporal_timestamp_in_closed_at(tmp_path: Path) -> None:
    csv_path = tmp_path / "naive_closed_at.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:59:59,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="closed_at timestamp must be UTC in CSV line 2"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_non_utc_offset_temporal_timestamp_in_closed_at(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "non_utc_closed_at.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:59:59+01:00,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="closed_at timestamp must be UTC in CSV line 2"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_closed_at_not_after_opened_at(tmp_path: Path) -> None:
    csv_path = tmp_path / "closed_at_not_after_opened.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:00:00Z,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="closed_at must be after opened_at"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_available_at_before_opened_at_when_closed_at_unknown(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "available_before_opened_without_closed.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,,2026-11-28T09:59:59Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="available_at must not be before opened_at"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_available_at_before_closed_at(tmp_path: Path) -> None:
    csv_path = tmp_path / "available_before_closed.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:59:59Z,2026-11-28T10:30:00Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="available_at must not be before closed_at"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_false_is_closed_with_known_closed_at(tmp_path: Path) -> None:
    csv_path = tmp_path / "false_with_closed_at.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,false
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="closed_at must be omitted"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_error_mentions_field_and_line_for_invalid_closed_at(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "error_field_line.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T09:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T09:59:59Z,2026-11-28T10:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1.1005,1.1015,1.0995,1.1010,120,not-a-timestamp,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="closed_at") as error_info:
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 8, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    assert "CSV line 3" in str(error_info.value)


def test_load_candle_records_rejects_invalid_is_closed_value(tmp_path: Path) -> None:
    csv_path = tmp_path / "invalid_bool.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,,,maybe
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Invalid is_closed value"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_temporal_contradiction(tmp_path: Path) -> None:
    csv_path = tmp_path / "invalid_temporal.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100,2026-11-28T09:59:59Z,2026-11-28T10:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_duplicate_opened_at_for_same_key(tmp_path: Path) -> None:
    csv_path = tmp_path / "duplicates.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        EURUSD,1h,2026-11-28T10:00:00Z,1.1005,1.1015,1.0995,1.1010,120
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Duplicate candle key"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candle_records_rejects_duplicates_outside_requested_range(tmp_path: Path) -> None:
    csv_path = tmp_path / "duplicates_outside_range.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T01:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        EURUSD,1h,2026-11-28T01:00:00Z,1.1001,1.1011,1.0991,1.1006,120
        EURUSD,1h,2026-11-28T10:00:00Z,1.1002,1.1012,1.0992,1.1007,130
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Duplicate candle key"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 10, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 10, 0, tzinfo=UTC),
            maximum_candles=1,
        )


def test_load_candle_records_aborts_when_file_changes_during_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "moving_target.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    original_fingerprint_builder = provider_module._build_file_fingerprint
    calls = {"count": 0}

    def changing_fingerprint(path: Path) -> tuple[str, int, int]:
        calls["count"] += 1
        fingerprint = original_fingerprint_builder(path)
        if calls["count"] == 2:
            return (fingerprint[0], fingerprint[1], fingerprint[2] + 1)
        return fingerprint

    monkeypatch.setattr(
        "elliottwaver.infrastructure.market_data.csv_market_data_provider._build_file_fingerprint",
        changing_fingerprint,
    )

    with pytest.raises(DomainError, match="changed during import"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_load_candles_reloads_after_fingerprint_change(tmp_path: Path) -> None:
    csv_path = tmp_path / "reload_after_change.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    first = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert str(first[0].close.value) == "1.1005"

    # Ensure file size changes so the fingerprint changes deterministically.
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1009,1000
        """,
    )

    second = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert str(second[0].close.value) == "1.1009"


def test_successful_invalid_and_successful_reload_sequence_for_records(tmp_path: Path) -> None:
    csv_path = tmp_path / "record_reload_sequence.csv"
    provider = CsvMarketDataProvider(csv_path=csv_path)

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        """,
    )
    first = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert str(first[0].candle.close.value) == "1.1005"

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1006,100,2026-11-28T09:00:00Z,2026-11-28T10:00:01Z,true
        """,
    )
    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1007,1000
        """,
    )
    third = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert str(third[0].candle.close.value) == "1.1007"


def test_provider_interfaces_read_unchanged_csv_only_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "single_read.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    original_read_rows = CsvMarketDataProvider._read_rows
    read_count = {"value": 0}

    def counting_read_rows(self: CsvMarketDataProvider) -> tuple[tuple[int, dict[str, str]], ...]:
        read_count["value"] += 1
        return original_read_rows(self)

    monkeypatch.setattr(CsvMarketDataProvider, "_read_rows", counting_read_rows)

    _ = provider.infer_request_spec()
    _ = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    _ = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert read_count["value"] == 1


def test_provider_order_legacy_before_temporal_uses_same_cached_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "legacy_before_temporal.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    original_read_rows = CsvMarketDataProvider._read_rows
    read_count = {"value": 0}

    def counting_read_rows(self: CsvMarketDataProvider) -> tuple[tuple[int, dict[str, str]], ...]:
        read_count["value"] += 1
        return original_read_rows(self)

    monkeypatch.setattr(CsvMarketDataProvider, "_read_rows", counting_read_rows)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert read_count["value"] == 1
    assert tuple(candle.opened_at for candle in candles) == tuple(
        record.candle.opened_at for record in records
    )


def test_provider_order_temporal_before_legacy_uses_same_cached_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "temporal_before_legacy.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    original_read_rows = CsvMarketDataProvider._read_rows
    read_count = {"value": 0}

    def counting_read_rows(self: CsvMarketDataProvider) -> tuple[tuple[int, dict[str, str]], ...]:
        read_count["value"] += 1
        return original_read_rows(self)

    monkeypatch.setattr(CsvMarketDataProvider, "_read_rows", counting_read_rows)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert read_count["value"] == 1
    assert tuple(record.candle.opened_at for record in records) == tuple(
        candle.opened_at for candle in candles
    )


def test_provider_orders_return_identical_results(tmp_path: Path) -> None:
    csv_path = tmp_path / "order_invariant.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T11:00:00Z,2,3,2,3,1,2026-11-28T11:59:59Z,2026-11-28T12:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        """,
    )

    provider_legacy_first = CsvMarketDataProvider(csv_path=csv_path)
    candles_lf = provider_legacy_first.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    records_lf = provider_legacy_first.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    provider_temporal_first = CsvMarketDataProvider(csv_path=csv_path)
    records_tf = provider_temporal_first.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    candles_tf = provider_temporal_first.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert candles_lf == candles_tf
    assert records_lf == records_tf


def test_infer_request_spec_detects_file_change(tmp_path: Path) -> None:
    csv_path = tmp_path / "infer_detects_change.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    first_spec = provider.infer_request_spec()

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        EURUSD,1h,2026-11-28T11:00:00Z,2,3,2,3,10
        """,
    )

    second_spec = provider.infer_request_spec()

    assert first_spec.end_time == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)
    assert second_spec.end_time == datetime(2026, 11, 28, 11, 0, tzinfo=UTC)


def test_load_candle_records_detects_temporal_metadata_only_changes(tmp_path: Path) -> None:
    csv_path = tmp_path / "temporal_only_change.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1,,,
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    first = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        """,
    )

    second = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert first[0].candle == second[0].candle
    assert first[0].temporal_semantics.is_closed is None
    assert second[0].temporal_semantics.is_closed is True
    assert second[0].temporal_semantics.closed_at == datetime(2026, 11, 28, 10, 59, 59, tzinfo=UTC)


def test_detected_file_change_during_import_does_not_publish_new_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "cache_publish_guard.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    _ = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    cached_before = object.__getattribute__(provider, "_cached_records")

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,3,10
        """,
    )

    original_fingerprint_builder = provider_module._build_file_fingerprint
    call_count = {"value": 0}

    def changing_fingerprint(path: Path) -> tuple[str, int, int]:
        call_count["value"] += 1
        fingerprint = original_fingerprint_builder(path)
        if call_count["value"] == 2:
            return (fingerprint[0], fingerprint[1], fingerprint[2] + 1)
        return fingerprint

    monkeypatch.setattr(
        "elliottwaver.infrastructure.market_data.csv_market_data_provider._build_file_fingerprint",
        changing_fingerprint,
    )

    with pytest.raises(DomainError, match="changed during import"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    cached_after = object.__getattribute__(provider, "_cached_records")
    assert cached_after is cached_before
    assert str(cached_after[0].candle.close.value) == "2"


def test_successful_invalid_invalid_successful_reload_sequence_for_load_candles(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "candle_reload_sequence.csv"
    provider = CsvMarketDataProvider(csv_path=csv_path)

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        """,
    )
    first = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert str(first[0].close.value) == "2"

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,3,1,2026-11-28T09:00:00Z,2026-11-28T10:00:01Z,true
        """,
    )
    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,4,1,4,10
        """,
    )
    third = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert str(third[0].close.value) == "4"


def test_successful_invalid_invalid_successful_reload_sequence_for_infer_request_spec(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "infer_reload_sequence.csv"
    provider = CsvMarketDataProvider(csv_path=csv_path)

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1
        """,
    )
    first_spec = provider.infer_request_spec()
    assert first_spec.end_time == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,3,1,2026-11-28T09:00:00Z,2026-11-28T10:00:01Z,true
        """,
    )
    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.infer_request_spec()

    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.infer_request_spec()

    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,4,1,4,1
        EURUSD,1h,2026-11-28T11:00:00Z,2,5,2,5,10
        """,
    )
    third_spec = provider.infer_request_spec()
    assert third_spec.end_time == datetime(2026, 11, 28, 11, 0, tzinfo=UTC)


def test_all_interfaces_reject_invalid_temporal_metadata(tmp_path: Path) -> None:
    csv_path = tmp_path / "all_interfaces_invalid_temporal.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1,2026-11-28T09:00:00Z,2026-11-28T10:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.infer_request_spec()

    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    with pytest.raises(DomainError, match="Temporal semantics invalid in CSV line"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_temporal_identical_duplicate_key_allowed_in_legacy_paths_but_not_records(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "identical_temporal_duplicates.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    spec = provider.infer_request_spec()
    assert spec.end_time == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert len(candles) == 2

    with pytest.raises(DomainError, match="Duplicate candle key"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_temporal_contradictory_duplicate_key_rejected_for_all_interfaces(tmp_path: Path) -> None:
    csv_path = tmp_path / "contradictory_temporal_duplicates.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T11:10:00Z,2026-11-28T11:10:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider.infer_request_spec()

    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_legacy_duplicates_without_temporal_metadata_remain_allowed(tmp_path: Path) -> None:
    csv_path = tmp_path / "legacy_duplicates_allowed.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert len(candles) == 2


def test_duplicate_key_with_missing_metadata_only_is_not_contradiction(tmp_path: Path) -> None:
    csv_path = tmp_path / "missing_metadata_duplicate.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,,,
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,,,
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert len(candles) == 2


def test_duplicate_key_with_none_vs_known_metadata_is_not_contradiction_in_legacy_paths(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "none_vs_known_metadata_duplicate.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,,,
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    spec = provider.infer_request_spec()
    assert spec.end_time == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert len(candles) == 2

    with pytest.raises(DomainError, match="Duplicate candle key"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_equal_opened_at_with_different_symbol_or_timeframe_is_allowed(tmp_path: Path) -> None:
    csv_path = tmp_path / "same_timestamp_other_symbol_timeframe.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        GBPUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        EURUSD,4h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T13:59:59Z,2026-11-28T14:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    assert len(records) == 1


def test_temporal_identical_duplicate_rejected_even_with_maximum_candles(tmp_path: Path) -> None:
    csv_path = tmp_path / "identical_duplicate_maximum.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Duplicate candle key"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 10, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 10, 0, tzinfo=UTC),
            maximum_candles=1,
        )


def test_temporal_contradiction_detected_across_three_records(tmp_path: Path) -> None:
    csv_path = tmp_path / "contradiction_three_records.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T11:10:00Z,2026-11-28T11:10:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider.infer_request_spec()

    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_fingerprint_normalization_is_windows_aware_without_forcing_linux_lowercase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "CaseSensitiveName.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1
        """,
    )

    monkeypatch.setattr(
        "elliottwaver.infrastructure.market_data.csv_market_data_provider.os.name",
        "posix",
    )
    posix_path, _, _ = provider_module._build_file_fingerprint(csv_path)

    monkeypatch.setattr(
        "elliottwaver.infrastructure.market_data.csv_market_data_provider.os.name",
        "nt",
    )
    windows_path, _, _ = provider_module._build_file_fingerprint(csv_path)

    assert any(character.isupper() for character in posix_path)
    assert windows_path == posix_path.lower()


def test_load_candle_records_reports_line_for_invalid_is_closed_value(tmp_path: Path) -> None:
    csv_path = tmp_path / "invalid_bool_with_line.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1,,,maybe
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Invalid is_closed value") as error_info:
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    assert "CSV line 2" in str(error_info.value)


def test_load_candle_records_reports_line_when_adapter_forces_opened_at_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "forced_opened_at_mismatch.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,2,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    def mismatching_temporal_semantics(
        *,
        row: dict[str, str],
        line_number: int,
        opened_at: datetime,
    ) -> CandleTemporalSemantics:
        _ = row
        _ = line_number
        return CandleTemporalSemantics(
            opened_at=opened_at + timedelta(hours=1),
            closed_at=None,
            available_at=None,
            is_closed=None,
        )

    monkeypatch.setattr(
        "elliottwaver.infrastructure.market_data.csv_market_data_provider._parse_temporal_semantics",
        mismatching_temporal_semantics,
    )

    with pytest.raises(
        DomainError,
        match="Temporal semantics opened_at mismatch in CSV line 2",
    ):
        provider.load_candle_records(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )


def test_legacy_and_record_views_return_identical_candles(tmp_path: Path) -> None:
    csv_path = tmp_path / "legacy_and_record_candle_equality.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        EURUSD,1h,2026-11-28T11:00:00Z,1.1005,1.1015,1.0995,1.1010,120
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    assert tuple(candles) == tuple(record.candle for record in records)


def test_duplicate_rules_legacy_compatible_are_order_invariant_per_instance(tmp_path: Path) -> None:
    csv_path = tmp_path / "legacy_compatible_duplicates_order_invariant.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,,,
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,,,
        """,
    )

    provider_infer_then_candles = CsvMarketDataProvider(csv_path=csv_path)
    spec_first = provider_infer_then_candles.infer_request_spec()
    candles_after = provider_infer_then_candles.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )

    provider_candles_then_infer = CsvMarketDataProvider(csv_path=csv_path)
    candles_first = provider_candles_then_infer.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
    )
    spec_after = provider_candles_then_infer.infer_request_spec()

    assert spec_first.end_time == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)
    assert spec_after.end_time == datetime(2026, 11, 28, 10, 0, tzinfo=UTC)
    assert len(candles_after) == 2
    assert len(candles_first) == 2


def test_duplicate_rules_contradictory_are_order_invariant_per_instance(tmp_path: Path) -> None:
    csv_path = tmp_path / "contradictory_duplicates_order_invariant.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume,closed_at,available_at,is_closed
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T10:59:59Z,2026-11-28T11:00:01Z,true
        EURUSD,1h,2026-11-28T10:00:00Z,1,3,1,2,1,2026-11-28T11:10:00Z,2026-11-28T11:10:01Z,true
        """,
    )

    provider_infer_then_candles = CsvMarketDataProvider(csv_path=csv_path)
    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider_infer_then_candles.infer_request_spec()
    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider_infer_then_candles.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )

    provider_candles_then_infer = CsvMarketDataProvider(csv_path=csv_path)
    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider_candles_then_infer.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 11, 28, 12, 0, tzinfo=UTC),
        )
    with pytest.raises(DomainError, match="contradictory temporal metadata"):
        provider_candles_then_infer.infer_request_spec()


def test_multiple_sequential_legacy_candles_keep_unknown_temporal_semantics(tmp_path: Path) -> None:
    csv_path = tmp_path / "legacy_sequential_unknown_semantics.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-11-28T10:00:00Z,1.1000,1.1010,1.0990,1.1005,100
        EURUSD,1h,2026-11-28T11:00:00Z,1.1005,1.1015,1.0995,1.1010,120
        EURUSD,1h,2026-11-28T12:00:00Z,1.1010,1.1020,1.1000,1.1015,140
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    records = provider.load_candle_records(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 11, 28, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 28, 13, 0, tzinfo=UTC),
    )

    assert len(records) == 3
    for record in records:
        semantics = record.temporal_semantics
        assert semantics.closed_at is None
        assert semantics.available_at is None
        assert semantics.is_closed is None
        assert semantics.confirmation_status(as_of=record.candle.opened_at) is (
            ConfirmationTimestampStatus.UNKNOWN
        )
