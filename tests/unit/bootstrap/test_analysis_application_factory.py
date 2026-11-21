from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from elliottwaver.application import (
    AnalysisApplication,
    AnalysisRequest,
    AnalyzeMultiTimeframeService,
    AnalyzeTimeframeService,
    CandleToSwingPreparationPort,
    TimeframeAnalysisRequest,
)
from elliottwaver.bootstrap import build_csv_analysis_application
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.infrastructure.analysis import PivotSwingPreparationAdapter
from elliottwaver.infrastructure.market_data import CsvMarketDataProvider

if TYPE_CHECKING:
    from pathlib import Path

    from elliottwaver.domain.market import Candle, Swing


class EmptySwingPreparationPort(CandleToSwingPreparationPort):
    def prepare_swings(
        self,
        candles: tuple[Candle, ...],
        request: TimeframeAnalysisRequest,
    ) -> tuple[Swing, ...]:
        _ = (candles, request)
        return ()


def test_build_csv_analysis_application_wires_expected_adapters(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "\n".join(
            (
                "symbol,timeframe,opened_at,open,high,low,close,volume",
                "EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    swing_port = EmptySwingPreparationPort()
    app = build_csv_analysis_application(
        csv_path=csv_path,
        swing_preparation_port=swing_port,
    )

    assert isinstance(app, AnalysisApplication)
    assert isinstance(app.analyze_use_case, AnalyzeMultiTimeframeService)

    assert isinstance(app.analyze_use_case, AnalyzeMultiTimeframeService)
    analyze_service = app.analyze_use_case
    timeframe_use_case = analyze_service.timeframe_use_case
    assert isinstance(timeframe_use_case, AnalyzeTimeframeService)
    assert isinstance(timeframe_use_case.market_data_provider, CsvMarketDataProvider)
    assert timeframe_use_case.swing_preparation_port is swing_port


def test_built_application_accepts_analysis_request(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "\n".join(
            (
                "symbol,timeframe,opened_at,open,high,low,close,volume",
                "EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    app = build_csv_analysis_application(
        csv_path=csv_path,
        swing_preparation_port=EmptySwingPreparationPort(),
    )

    request = AnalysisRequest(
        symbol=Symbol("EURUSD"),
        timeframe_requests=(
            TimeframeAnalysisRequest(
                symbol=Symbol("EURUSD"),
                timeframe=MarketTimeframe.ONE_HOUR,
                start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                end_time=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
            ),
        ),
        start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
    )

    # Empty swing preparation keeps the test focused on wiring and request flow.
    result = app.analyze_use_case.analyze(request)

    assert result.metadata.symbol == Symbol("EURUSD")
    assert result.metadata.requested_timeframes == (MarketTimeframe.ONE_HOUR,)


def test_build_csv_analysis_application_accepts_test_double_override(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "\n".join(
            (
                "symbol,timeframe,opened_at,open,high,low,close,volume",
                "EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    swing_port = EmptySwingPreparationPort()
    app = build_csv_analysis_application(
        csv_path=csv_path,
        swing_preparation_port=swing_port,
    )

    assert isinstance(app.analyze_use_case, AnalyzeMultiTimeframeService)
    analyze_service = app.analyze_use_case
    timeframe_use_case = analyze_service.timeframe_use_case
    assert isinstance(timeframe_use_case, AnalyzeTimeframeService)
    assert timeframe_use_case.swing_preparation_port is swing_port


def test_build_csv_analysis_application_uses_productive_default_swing_port(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "\n".join(
            (
                "symbol,timeframe,opened_at,open,high,low,close,volume",
                "EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    app = build_csv_analysis_application(csv_path=csv_path)

    assert isinstance(app.analyze_use_case, AnalyzeMultiTimeframeService)
    analyze_service = app.analyze_use_case
    timeframe_use_case = analyze_service.timeframe_use_case
    assert isinstance(timeframe_use_case, AnalyzeTimeframeService)
    assert isinstance(timeframe_use_case.swing_preparation_port, PivotSwingPreparationAdapter)
