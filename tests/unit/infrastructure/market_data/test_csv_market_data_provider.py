from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.infrastructure.market_data import CsvMarketDataProvider

if TYPE_CHECKING:
    from pathlib import Path


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _write_csv_with_bom(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8-sig")


def test_load_candles_filters_and_sorts_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T02:00:00Z,100,112,99,108,10
        EURUSD,1h,2026-07-21T01:00:00Z,98,106,95,102,9
        EURUSD,4h,2026-07-21T01:00:00Z,98,106,95,102,9
        GBPUSD,1h,2026-07-21T01:00:00Z,98,106,95,102,9
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
        end_time=datetime(2026, 7, 21, 3, 0, tzinfo=UTC),
    )

    assert len(candles) == 2
    assert candles[0].opened_at == datetime(2026, 7, 21, 1, 0, tzinfo=UTC)
    assert candles[1].opened_at == datetime(2026, 7, 21, 2, 0, tzinfo=UTC)


def test_load_candles_applies_maximum_candles_to_latest_entries(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        EURUSD,1h,2026-07-21T01:00:00Z,104,111,100,108,10
        EURUSD,1h,2026-07-21T02:00:00Z,108,115,105,112,10
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 7, 21, 3, 0, tzinfo=UTC),
        maximum_candles=2,
    )

    assert len(candles) == 2
    assert candles[0].opened_at == datetime(2026, 7, 21, 1, 0, tzinfo=UTC)
    assert candles[1].opened_at == datetime(2026, 7, 21, 2, 0, tzinfo=UTC)


def test_load_candles_rejects_missing_required_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="missing required columns"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 7, 21, 3, 0, tzinfo=UTC),
        )


def test_load_candles_rejects_non_utc_timestamp(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00+01:00,100,110,95,104,10
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="Timestamp must be UTC"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 7, 21, 3, 0, tzinfo=UTC),
        )


def test_infer_request_spec_returns_symbol_timeframe_and_range(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T02:00:00Z,100,112,99,108,10
        EURUSD,1h,2026-07-21T00:00:00Z,98,106,95,102,9
        EURUSD,1h,2026-07-21T01:00:00Z,99,108,96,104,9
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    spec = provider.infer_request_spec()

    assert spec.symbol == Symbol("EURUSD")
    assert spec.timeframe is MarketTimeframe.ONE_HOUR
    assert spec.start_time == datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    assert spec.end_time == datetime(2026, 7, 21, 2, 0, tzinfo=UTC)


def test_infer_request_spec_rejects_mixed_symbols(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        GBPUSD,1h,2026-07-21T01:00:00Z,101,111,96,105,10
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="exactly one symbol"):
        provider.infer_request_spec()


def test_infer_request_spec_rejects_mixed_timeframes(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        EURUSD,4h,2026-07-21T01:00:00Z,101,111,96,105,10
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="exactly one timeframe"):
        provider.infer_request_spec()


def test_load_candles_accepts_utf8_with_bom_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles_bom.csv"
    _write_csv_with_bom(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    candles = provider.load_candles(
        symbol=Symbol("EURUSD"),
        timeframe=MarketTimeframe.ONE_HOUR,
        start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
    )

    assert len(candles) == 1
    assert candles[0].symbol == Symbol("EURUSD")


def test_infer_request_spec_accepts_utf8_with_bom_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles_bom.csv"
    _write_csv_with_bom(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T02:00:00Z,100,112,99,108,10
        EURUSD,1h,2026-07-21T00:00:00Z,98,106,95,102,9
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    spec = provider.infer_request_spec()

    assert spec.symbol == Symbol("EURUSD")
    assert spec.timeframe is MarketTimeframe.ONE_HOUR
    assert spec.start_time == datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    assert spec.end_time == datetime(2026, 7, 21, 2, 0, tzinfo=UTC)


def test_load_candles_rejects_missing_symbol_column_with_bom_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles_bom_missing_symbol.csv"
    _write_csv_with_bom(
        csv_path,
        """
        timeframe,opened_at,open,high,low,close,volume
        1h,2026-07-21T00:00:00Z,100,110,95,104,10
        """,
    )
    provider = CsvMarketDataProvider(csv_path=csv_path)

    with pytest.raises(DomainError, match="missing required columns: symbol"):
        provider.load_candles(
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
        )
