from __future__ import annotations

from elliottwaver import interfaces
from elliottwaver.interfaces import analysis


def test_interfaces_package_exports_desktop_entrypoints_only() -> None:
    assert interfaces.__all__ == [
        "AnalysisDesktopTkApp",
        "DesktopAnalysisPresentation",
        "launch_analysis_desktop",
        "present_csv_analysis",
    ]


def test_interfaces_analysis_exports_curated_contract_surface() -> None:
    assert analysis.__all__ == [
        "AnalysisApplication",
        "AnalysisApplicationResult",
        "AnalysisRequest",
        "AnalysisResponse",
        "CandleToSwingPreparationPort",
        "ForecastUseCase",
        "MarketDataProvider",
        "TimeframeAnalysisRequest",
    ]
