"""Composition helpers for building the analysis application."""

from __future__ import annotations

from pathlib import Path

from elliottwaver.application import (
    AnalysisApplication,
    AnalyzeMultiTimeframeService,
    AnalyzeTimeframeService,
    CandleToSwingPreparationPort,
)
from elliottwaver.application.forecast import ForecastEngine
from elliottwaver.infrastructure.analysis import (
    PivotSwingPreparationAdapter,
    SystemAnalysisClock,
    UuidAnalysisIdProvider,
)
from elliottwaver.infrastructure.market_data import CsvMarketDataProvider


def build_csv_analysis_application(
    *,
    csv_path: str | Path,
    swing_preparation_port: CandleToSwingPreparationPort | None = None,
) -> AnalysisApplication:
    """Build a CSV-backed analysis application with infrastructure adapters."""

    analysis_clock = SystemAnalysisClock()
    analysis_id_provider = UuidAnalysisIdProvider()
    timeframe_use_case = AnalyzeTimeframeService(
        market_data_provider=CsvMarketDataProvider(csv_path=Path(csv_path)),
        swing_preparation_port=swing_preparation_port or PivotSwingPreparationAdapter(),
        analysis_clock=analysis_clock,
        analysis_id_provider=analysis_id_provider,
    )
    analyze_use_case = AnalyzeMultiTimeframeService(
        timeframe_use_case=timeframe_use_case,
        analysis_clock=analysis_clock,
        analysis_id_provider=analysis_id_provider,
    )

    return AnalysisApplication(
        analyze_use_case=analyze_use_case,
        forecast_engine=ForecastEngine(),
    )
