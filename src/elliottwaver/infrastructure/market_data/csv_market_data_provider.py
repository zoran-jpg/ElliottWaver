"""CSV-backed market-data adapter for the analysis application port."""

from __future__ import annotations

import os
from csv import DictReader
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from elliottwaver.application import MarketDataProvider
from elliottwaver.application.temporal_market_data import (
    TemporalCandleRecord,
    TemporalMarketDataProvider,
)
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Candle, CandleTemporalSemantics, Price

_REQUIRED_COLUMNS: tuple[str, ...] = (
    "symbol",
    "timeframe",
    "opened_at",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


@dataclass(frozen=True, slots=True)
class CsvRequestSpec:
    """Canonical analysis request metadata inferred from one CSV source."""

    symbol: Symbol
    timeframe: MarketTimeframe
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True)
class CsvMarketDataProvider(MarketDataProvider, TemporalMarketDataProvider):
    """Load candles from a deterministic CSV source."""

    csv_path: Path
    _cached_records: tuple[TemporalCandleRecord, ...] | None = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
    )
    _cached_fingerprint: tuple[str, int, int] | None = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
    )

    def infer_request_spec(self) -> CsvRequestSpec:
        """Infer symbol, timeframe, and UTC range for a single-instrument CSV file."""

        candles = self._load_all_candles()
        if not candles:
            message = "CSV file does not contain any candle rows"
            raise DomainError(message)

        symbols = {candle.symbol for candle in candles}
        if len(symbols) != 1:
            message = "CSV must contain exactly one symbol"
            raise DomainError(message)

        timeframes = {candle.timeframe for candle in candles}
        if len(timeframes) != 1:
            message = "CSV must contain exactly one timeframe"
            raise DomainError(message)

        return CsvRequestSpec(
            symbol=candles[0].symbol,
            timeframe=candles[0].timeframe,
            start_time=candles[0].opened_at,
            end_time=candles[-1].opened_at,
        )

    def load_candles(
        self,
        symbol: Symbol,
        timeframe: MarketTimeframe,
        start_time: datetime,
        end_time: datetime,
        maximum_candles: int | None = None,
    ) -> tuple[Candle, ...]:
        """Return candles filtered by request fields and sorted by opened_at."""

        if maximum_candles is not None and maximum_candles <= 0:
            message = "maximum_candles must be greater than 0 when provided"
            raise DomainError(message)

        candles = self._load_all_candles()
        filtered = tuple(
            candle
            for candle in candles
            if candle.symbol == symbol
            and candle.timeframe is timeframe
            and start_time <= candle.opened_at <= end_time
        )

        if maximum_candles is None:
            return filtered

        return filtered[-maximum_candles:]

    def load_candle_records(
        self,
        symbol: Symbol,
        timeframe: MarketTimeframe,
        start_time: datetime,
        end_time: datetime,
        maximum_candles: int | None = None,
    ) -> tuple[TemporalCandleRecord, ...]:
        """Return temporal candle records filtered by request fields."""

        if maximum_candles is not None and maximum_candles <= 0:
            message = "maximum_candles must be greater than 0 when provided"
            raise DomainError(message)

        records = self._load_all_records()
        _validate_unique_opened_at_keys(records)
        filtered = tuple(
            record
            for record in records
            if record.candle.symbol == symbol
            and record.candle.timeframe is timeframe
            and start_time <= record.candle.opened_at <= end_time
        )

        if maximum_candles is None:
            return filtered

        return filtered[-maximum_candles:]

    def _load_all_candles(self) -> tuple[Candle, ...]:
        records = self._load_all_records()
        return tuple(record.candle for record in records)

    def _load_all_records(self) -> tuple[TemporalCandleRecord, ...]:
        csv_file = Path(self.csv_path)
        fingerprint_before = _build_file_fingerprint(csv_file)
        cached_records = self._cached_records
        if cached_records is not None and self._cached_fingerprint == fingerprint_before:
            return cached_records

        rows = self._read_rows()
        records = tuple(
            sorted(
                (
                    self._parse_candle_record(row=row, line_number=line_number)
                    for line_number, row in rows
                ),
                key=lambda record: record.candle.opened_at,
            )
        )
        _validate_explicit_temporal_duplicate_keys(records)

        fingerprint_after = _build_file_fingerprint(csv_file)
        if fingerprint_after != fingerprint_before:
            message = "CSV file changed during import; import aborted for consistency"
            raise DomainError(message)

        object.__setattr__(self, "_cached_records", records)
        object.__setattr__(self, "_cached_fingerprint", fingerprint_after)
        return records

    def _read_rows(self) -> tuple[tuple[int, dict[str, str]], ...]:
        csv_file = Path(self.csv_path)
        if not csv_file.exists() or not csv_file.is_file():
            message = f"CSV file does not exist: {csv_file}"
            raise DomainError(message)

        with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = DictReader(handle)
            fieldnames = reader.fieldnames
            if fieldnames is None:
                message = "CSV header is required"
                raise DomainError(message)

            missing_columns = tuple(
                column_name for column_name in _REQUIRED_COLUMNS if column_name not in fieldnames
            )
            if missing_columns:
                message = f"CSV is missing required columns: {', '.join(missing_columns)}"
                raise DomainError(message)

            return tuple(enumerate(reader, start=2))

    def _parse_candle_record(
        self,
        *,
        row: dict[str, str],
        line_number: int,
    ) -> TemporalCandleRecord:
        try:
            volume = Decimal(row["volume"])
        except (InvalidOperation, ValueError) as error:
            message = f"Invalid volume in CSV line {line_number}"
            raise DomainError(message) from error

        try:
            candle = Candle(
                symbol=Symbol(row["symbol"]),
                timeframe=MarketTimeframe.parse(row["timeframe"]),
                opened_at=_parse_utc_timestamp(row["opened_at"], line_number=line_number),
                open=Price.parse(row["open"]),
                high=Price.parse(row["high"]),
                low=Price.parse(row["low"]),
                close=Price.parse(row["close"]),
                volume=volume,
            )
        except ValueError as error:
            message = f"Invalid candle row in CSV line {line_number}"
            raise DomainError(message) from error

        temporal_semantics = _parse_temporal_semantics(
            row=row,
            line_number=line_number,
            opened_at=candle.opened_at,
        )
        try:
            return TemporalCandleRecord(
                candle=candle,
                temporal_semantics=temporal_semantics,
            )
        except DomainError as error:
            message = f"Temporal semantics opened_at mismatch in CSV line {line_number}"
            raise DomainError(message) from error


def _parse_utc_timestamp(value: str, *, line_number: int) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        message = f"Invalid timestamp in CSV line {line_number}"
        raise DomainError(message) from error

    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(None):
        message = f"Timestamp must be UTC in CSV line {line_number}"
        raise DomainError(message)

    return parsed.astimezone(UTC)


def _parse_optional_utc_timestamp(
    value: str | None,
    *,
    line_number: int,
    field_name: str,
) -> datetime | None:
    if value is None or value.strip() == "":
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        message = f"Invalid {field_name} timestamp in CSV line {line_number}"
        raise DomainError(message) from error

    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(None):
        message = f"{field_name} timestamp must be UTC in CSV line {line_number}"
        raise DomainError(message)

    return parsed.astimezone(UTC)


def _parse_optional_bool(value: str | None, *, line_number: int) -> bool | None:
    if value is None or value.strip() == "":
        return None

    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False

    message = f"Invalid is_closed value in CSV line {line_number}: expected true|false"
    raise DomainError(message)


def _parse_temporal_semantics(
    *,
    row: dict[str, str],
    line_number: int,
    opened_at: datetime,
) -> CandleTemporalSemantics:
    try:
        return CandleTemporalSemantics(
            opened_at=opened_at,
            closed_at=_parse_optional_utc_timestamp(
                row.get("closed_at"),
                line_number=line_number,
                field_name="closed_at",
            ),
            available_at=_parse_optional_utc_timestamp(
                row.get("available_at"),
                line_number=line_number,
                field_name="available_at",
            ),
            is_closed=_parse_optional_bool(row.get("is_closed"), line_number=line_number),
        )
    except DomainError as error:
        message = f"Temporal semantics invalid in CSV line {line_number}: {error}"
        raise DomainError(message) from error


def _build_file_fingerprint(csv_file: Path) -> tuple[str, int, int]:
    if not csv_file.exists() or not csv_file.is_file():
        message = f"CSV file does not exist: {csv_file}"
        raise DomainError(message)

    stat_result = csv_file.stat()
    normalized_path = csv_file.resolve().as_posix()
    if os.name == "nt":
        normalized_path = normalized_path.lower()
    return (normalized_path, stat_result.st_size, stat_result.st_mtime_ns)


def _validate_explicit_temporal_duplicate_keys(records: tuple[TemporalCandleRecord, ...]) -> None:
    records_by_key: dict[tuple[Symbol, MarketTimeframe, datetime], list[TemporalCandleRecord]] = {}
    for record in records:
        key = (record.candle.symbol, record.candle.timeframe, record.candle.opened_at)
        records_by_key.setdefault(key, []).append(record)

    for key_records in records_by_key.values():
        if len(key_records) <= 1:
            continue

        if _has_contradictory_known_temporal_metadata(key_records):
            message = (
                "Duplicate candle key (symbol,timeframe,opened_at) "
                "with contradictory temporal metadata in CSV source"
            )
            raise DomainError(message)


def _has_explicit_temporal_metadata(temporal_semantics: CandleTemporalSemantics) -> bool:
    return (
        temporal_semantics.closed_at is not None
        or temporal_semantics.available_at is not None
        or temporal_semantics.is_closed is not None
    )


def _has_contradictory_known_temporal_metadata(records: list[TemporalCandleRecord]) -> bool:
    if not any(_has_explicit_temporal_metadata(record.temporal_semantics) for record in records):
        return False

    known_closed_at = {
        record.temporal_semantics.closed_at
        for record in records
        if record.temporal_semantics.closed_at is not None
    }
    if len(known_closed_at) > 1:
        return True

    known_available_at = {
        record.temporal_semantics.available_at
        for record in records
        if record.temporal_semantics.available_at is not None
    }
    if len(known_available_at) > 1:
        return True

    known_is_closed = {
        record.temporal_semantics.is_closed
        for record in records
        if record.temporal_semantics.is_closed is not None
    }
    return len(known_is_closed) > 1


def _validate_unique_opened_at_keys(records: tuple[TemporalCandleRecord, ...]) -> None:
    seen_keys: set[tuple[Symbol, MarketTimeframe, datetime]] = set()
    for record in records:
        key = (record.candle.symbol, record.candle.timeframe, record.candle.opened_at)
        if key in seen_keys:
            message = "Duplicate candle key (symbol,timeframe,opened_at) in CSV source"
            raise DomainError(message)
        seen_keys.add(key)
