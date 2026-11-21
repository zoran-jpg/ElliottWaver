"""CSV-backed market-data adapter for the analysis application port."""

from __future__ import annotations

from csv import DictReader
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from elliottwaver.application import MarketDataProvider
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.market import Candle, Price

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
class CsvMarketDataProvider(MarketDataProvider):
    """Load candles from a deterministic CSV source."""

    csv_path: Path

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

    def _load_all_candles(self) -> tuple[Candle, ...]:
        rows = self._read_rows()
        return tuple(
            sorted(
                (self._parse_candle(row=row, line_number=line_number) for line_number, row in rows),
                key=lambda candle: candle.opened_at,
            )
        )

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

    def _parse_candle(self, *, row: dict[str, str], line_number: int) -> Candle:
        try:
            volume = Decimal(row["volume"])
        except (InvalidOperation, ValueError) as error:
            message = f"Invalid volume in CSV line {line_number}"
            raise DomainError(message) from error

        try:
            return Candle(
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
