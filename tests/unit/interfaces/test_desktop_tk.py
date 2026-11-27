from __future__ import annotations

import threading
import tkinter as tk
from contextlib import suppress
from csv import DictReader
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar, Protocol

import pytest
from tests.unit.application.forecast.test_forecast_engine import make_analysis_response
from tests.unit.domain.context.helpers import make_selected_wave_candidate

from elliottwaver.application import AnalysisApplicationResult
from elliottwaver.application.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalyzeMultiTimeframeService,
)
from elliottwaver.application.chart_contract import (
    ChartCandle,
    ChartDataContract,
    ChartFibonacciProjection,
    ChartForecastScenario,
    ChartProjectionTarget,
    TimeframeChartData,
)
from elliottwaver.application.forecast import ForecastEngine
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.forecast import ForecastResult
from elliottwaver.domain.market import Candle, Price
from elliottwaver.domain.patterns import (
    CandleTemporalSemantics,
    ConfirmationTimestampStatus,
    detect_candlestick_patterns,
    detect_candlestick_patterns_with_temporal_confirmation,
)
from elliottwaver.infrastructure.market_data import CsvMarketDataProvider
from elliottwaver.interfaces.desktop_tk import (
    AnalysisDesktopTkApp,
    CsvAnalysisRequestSpec,
    DesktopAnalysisController,
    DesktopAnalysisPresentation,
    build_analysis_request,
    format_analysis_overview,
    format_analysis_result,
    human_readable_error,
    infer_request_spec_from_csv,
    launch_analysis_desktop,
    present_csv_analysis,
    run_analysis_from_csv,
)


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def test_infer_request_spec_from_csv_derives_symbol_timeframe_and_range(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T02:00:00Z,100,110,95,104,10
        EURUSD,1h,2026-07-21T00:00:00Z,99,111,97,103,11
        """,
    )

    spec = infer_request_spec_from_csv(csv_path)

    assert spec.symbol == "EURUSD"
    assert spec.timeframe == "1h"
    assert spec.start_time == datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    assert spec.end_time == datetime(2026, 7, 21, 2, 0, tzinfo=UTC)


def test_infer_request_spec_from_csv_rejects_non_utc_timestamp(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T02:00:00+01:00,100,110,95,104,10
        """,
    )

    with pytest.raises(DomainError, match="Timestamp must be UTC"):
        infer_request_spec_from_csv(csv_path)


def test_infer_request_spec_from_csv_rejects_empty_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(csv_path, "")

    with pytest.raises(DomainError, match="missing required columns"):
        infer_request_spec_from_csv(csv_path)


def test_infer_request_spec_from_csv_rejects_mixed_symbols(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        GBPUSD,1h,2026-07-21T01:00:00Z,101,111,96,105,10
        """,
    )

    with pytest.raises(DomainError, match="exactly one symbol"):
        infer_request_spec_from_csv(csv_path)


def test_infer_request_spec_from_csv_rejects_mixed_timeframes(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        EURUSD,4h,2026-07-21T01:00:00Z,101,111,96,105,10
        """,
    )

    with pytest.raises(DomainError, match="exactly one timeframe"):
        infer_request_spec_from_csv(csv_path)


def test_build_analysis_request_maps_spec_values() -> None:
    spec = CsvAnalysisRequestSpec(
        symbol="EURUSD",
        timeframe="1h",
        start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
    )

    request = build_analysis_request(spec)

    assert request.symbol.value == "EURUSD"
    assert request.timeframe_requests[0].timeframe.value == "1h"
    assert request.start_time == spec.start_time
    assert request.end_time == spec.end_time


def test_build_analysis_request_rejects_invalid_domain_data() -> None:
    spec = CsvAnalysisRequestSpec(
        symbol="eur usd",
        timeframe="1h",
        start_time=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="Invalid market symbol"):
        build_analysis_request(spec)


def test_format_analysis_result_renders_forecast_confidence_and_projections() -> None:
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )
    forecast = ForecastEngine().generate(analysis)
    result = AnalysisApplicationResult(analysis=analysis, forecast=forecast)

    confidence_text, forecast_text, projection_text = format_analysis_result(result)

    assert confidence_text.endswith("%")
    assert "Szenario:" in forecast_text
    assert "Erwartete Welle:" in forecast_text
    assert "->" in projection_text


def test_format_analysis_result_handles_empty_projections() -> None:
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )
    forecast = ForecastEngine().generate(analysis)
    no_projection_forecast = ForecastResult(
        primary_scenario=forecast.primary_scenario,
        alternative_scenarios=forecast.alternative_scenarios,
        projection_quality=forecast.projection_quality,
        overall_confidence=Decimal(forecast.overall_confidence),
        projections=(),
    )
    result = AnalysisApplicationResult(analysis=analysis, forecast=no_projection_forecast)

    _confidence, _forecast_text, projection_text = format_analysis_result(result)

    assert projection_text == "Keine Fibonacci-Projektionen verfugbar."


def test_format_analysis_overview_renders_stage_symbol_and_issues() -> None:
    analysis = make_analysis_response(
        selected_wave=make_selected_wave_candidate(score_percent="90"),
        confluence_percent="80",
    )
    forecast = ForecastEngine().generate(analysis)
    result = AnalysisApplicationResult(analysis=analysis, forecast=forecast)

    overview = format_analysis_overview(result)

    assert "Stage:" in overview
    assert "Symbol:" in overview
    assert "Timeframes angefragt:" in overview
    assert "Issues:" in overview


def test_human_readable_error_contains_user_hint() -> None:
    message = human_readable_error(DomainError("invalid csv"))

    assert "Analyse konnte nicht ausgefuhrt werden." in message
    assert "Bitte CSV-Format" in message


def test_human_readable_error_for_incomplete_analysis_is_actionable() -> None:
    message = human_readable_error(
        DomainError("analysis must be completed before forecast generation")
    )

    assert "noch keinen abgeschlossenen Forecast" in message
    assert "erneut starten" in message


def test_present_csv_analysis_reports_missing_file() -> None:
    presentation = present_csv_analysis(Path("C:/__missing__/candles.csv"))

    assert presentation.status == "Analyse fehlgeschlagen"
    assert presentation.error_text is not None
    assert "Analyse konnte nicht ausgefuhrt werden" in presentation.error_text


def test_present_csv_analysis_reports_unreadable_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        """,
    )

    def fake_open(*_args: object, **_kwargs: object) -> object:
        message = "access denied"
        raise PermissionError(message)

    monkeypatch.setattr(Path, "open", fake_open)

    presentation = present_csv_analysis(csv_path)

    assert presentation.status == "Analyse fehlgeschlagen"
    assert presentation.error_text is not None
    assert "Analyse konnte nicht ausgefuhrt werden" in presentation.error_text


def test_present_csv_analysis_reports_invalid_csv_format(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95
        """,
    )

    presentation = present_csv_analysis(csv_path)

    assert presentation.status == "Analyse fehlgeschlagen"
    assert presentation.error_text is not None
    assert "CSV-Format" in presentation.error_text


def test_present_csv_analysis_e2e_like_pipeline_to_presenter(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,104,108,103,105,10
        EURUSD,1h,2026-07-21T01:00:00Z,101,106,100,103,10
        EURUSD,1h,2026-07-21T02:00:00Z,107,110,105,109,10
        EURUSD,1h,2026-07-21T03:00:00Z,105,107,104,106,10
        EURUSD,1h,2026-07-21T04:00:00Z,119,125,118,123,10
        EURUSD,1h,2026-07-21T05:00:00Z,117,120,116,118,10
        EURUSD,1h,2026-07-21T06:00:00Z,124,132,123,130,10
        EURUSD,1h,2026-07-21T07:00:00Z,123,128,121,126,10
        """,
    )

    presentation = present_csv_analysis(csv_path)

    assert presentation.status == "Analyse abgeschlossen"
    assert presentation.error_text is None
    assert "Stage:" in presentation.result_text


def test_present_csv_analysis_populates_support_resistance_zones_from_engineering_fixture() -> None:
    fixture = Path(__file__).resolve().parents[3] / "engineering" / "testdata" / "swing_e2e_100.csv"

    presentation = present_csv_analysis(fixture)

    assert presentation.status == "Analyse abgeschlossen"
    assert presentation.chart_data is not None
    timeframe = presentation.chart_data.timeframe_data[0]
    assert len(timeframe.support_resistance_zones) > 0
    assert len(timeframe.support_resistance_zones) > 10
    assert all(
        zone.zone_type in {"support", "resistance"} for zone in timeframe.support_resistance_zones
    )


def test_candlestick_fixture_detects_expected_pattern_families() -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "engineering"
        / "testdata"
        / "candlestick_patterns_e2e.csv"
    )

    provider = CsvMarketDataProvider(csv_path=fixture)
    spec = provider.infer_request_spec()
    candles = provider.load_candles(
        symbol=spec.symbol,
        timeframe=spec.timeframe,
        start_time=spec.start_time,
        end_time=spec.end_time,
    )
    patterns = detect_candlestick_patterns(candles=candles)

    counts: dict[str, int] = {}
    for pattern in patterns:
        counts[pattern.pattern_type] = counts.get(pattern.pattern_type, 0) + 1
        assert pattern.confirmed_at is None
        assert pattern.confirmation_status.value == "unknown"
        assert pattern.ended_at == pattern.candle_timestamps[-1]

    assert counts == {
        "bearish_engulfing": 2,
        "bearish_three_line_strike": 1,
        "bullish_engulfing": 2,
        "bullish_three_line_strike": 1,
        "dragonfly_doji": 1,
        "gravestone_doji": 1,
        "hammer": 1,
        "shooting_star": 1,
        "tweezer_bottom": 3,
        "tweezer_top": 3,
    }


def test_candlestick_pattern_fixture_is_prefix_invariant() -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "engineering"
        / "testdata"
        / "candlestick_patterns_e2e.csv"
    )
    rows = fixture.read_text(encoding="utf-8").splitlines()

    candles: list[Candle] = []
    for row in rows[1:]:
        symbol, timeframe, opened_at, open_price, high, low, close, volume = row.split(",")
        candles.append(
            Candle(
                symbol=Symbol(symbol),
                timeframe=MarketTimeframe(timeframe),
                opened_at=datetime.fromisoformat(opened_at.replace("Z", "+00:00")),
                open=Price.parse(open_price),
                high=Price.parse(high),
                low=Price.parse(low),
                close=Price.parse(close),
                volume=Decimal(volume),
            )
        )

    full_patterns = detect_candlestick_patterns(candles=tuple(candles))
    prefix = tuple(candles[:12])
    prefix_patterns = detect_candlestick_patterns(candles=prefix)
    cutoff = prefix[-1].opened_at
    full_prefix = tuple(pattern for pattern in full_patterns if pattern.ended_at <= cutoff)

    assert prefix_patterns == full_prefix


def test_temporal_semantics_fixture_supports_as_of_confirmation_and_unknown_states() -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "engineering"
        / "testdata"
        / "candlestick_patterns_temporal_semantics.csv"
    )
    candles: list[Candle] = []
    semantics: dict[datetime, CandleTemporalSemantics] = {}

    with fixture.open("r", encoding="utf-8", newline="") as handle:
        for row in DictReader(handle):
            opened_at = datetime.fromisoformat(row["opened_at"].replace("Z", "+00:00"))
            candles.append(
                Candle(
                    symbol=Symbol(row["symbol"]),
                    timeframe=MarketTimeframe(row["timeframe"]),
                    opened_at=opened_at,
                    open=Price.parse(row["open"]),
                    high=Price.parse(row["high"]),
                    low=Price.parse(row["low"]),
                    close=Price.parse(row["close"]),
                    volume=Decimal(row["volume"]),
                )
            )

            closed_at_raw = row["closed_at"].strip()
            available_at_raw = row["available_at"].strip()
            is_closed_raw = row["is_closed"].strip().lower()
            semantics[opened_at] = CandleTemporalSemantics(
                opened_at=opened_at,
                closed_at=(
                    datetime.fromisoformat(closed_at_raw.replace("Z", "+00:00"))
                    if closed_at_raw
                    else None
                ),
                available_at=(
                    datetime.fromisoformat(available_at_raw.replace("Z", "+00:00"))
                    if available_at_raw
                    else None
                ),
                is_closed=(
                    True if is_closed_raw == "true" else False if is_closed_raw == "false" else None
                ),
            )

    patterns_before = detect_candlestick_patterns_with_temporal_confirmation(
        candles=tuple(candles[:2]),
        temporal_semantics_by_opened_at=semantics,
        as_of=datetime(2026, 7, 22, 2, 11, tzinfo=UTC),
    )
    patterns_after = detect_candlestick_patterns_with_temporal_confirmation(
        candles=tuple(candles[:2]),
        temporal_semantics_by_opened_at=semantics,
        as_of=datetime(2026, 7, 22, 2, 12, tzinfo=UTC),
    )

    assert len(patterns_before) == 1
    assert patterns_before[0].confirmation_status is ConfirmationTimestampStatus.PENDING
    assert patterns_before[0].confirmed_at is None

    assert len(patterns_after) == 1
    assert patterns_after[0].confirmation_status is ConfirmationTimestampStatus.CONFIRMED
    assert patterns_after[0].confirmed_at == datetime(2026, 7, 22, 2, 12, tzinfo=UTC)

    unknown_semantics = dict(semantics)
    unknown_semantics[candles[1].opened_at] = CandleTemporalSemantics(
        opened_at=candles[1].opened_at,
        closed_at=datetime(2026, 7, 22, 2, 0, tzinfo=UTC),
        available_at=datetime(2026, 7, 22, 2, 12, tzinfo=UTC),
        is_closed=None,
    )
    unknown_status_pattern = detect_candlestick_patterns_with_temporal_confirmation(
        candles=tuple(candles[:2]),
        temporal_semantics_by_opened_at=unknown_semantics,
        as_of=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
    )[0]
    assert unknown_status_pattern.confirmation_status is ConfirmationTimestampStatus.UNKNOWN
    assert unknown_status_pattern.confirmed_at is None


def test_run_analysis_from_csv_returns_partial_result_for_incomplete_analysis(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,100,110,95,104,10
        EURUSD,1h,2026-07-21T01:00:00Z,104,114,99,109,11
        """,
    )

    result = run_analysis_from_csv(csv_path)

    assert result.analysis.stage.value != "completed"
    assert result.forecast.is_empty is True
    assert result.forecast.primary_scenario is None
    assert result.forecast.projections == ()


def test_run_analysis_from_csv_returns_result_for_valid_swings(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,104,108,103,105,10
        EURUSD,1h,2026-07-21T01:00:00Z,101,106,100,103,10
        EURUSD,1h,2026-07-21T02:00:00Z,107,110,105,109,10
        EURUSD,1h,2026-07-21T03:00:00Z,105,107,104,106,10
        EURUSD,1h,2026-07-21T04:00:00Z,119,125,118,123,10
        EURUSD,1h,2026-07-21T05:00:00Z,117,120,116,118,10
        EURUSD,1h,2026-07-21T06:00:00Z,124,132,123,130,10
        EURUSD,1h,2026-07-21T07:00:00Z,123,128,121,126,10
        """,
    )

    result = run_analysis_from_csv(csv_path)

    assert result.analysis.stage.value == "completed"
    assert result.forecast.primary_scenario is not None
    assert len(result.forecast.projections) > 0


class _Runnable(Protocol):
    def __call__(self, *args: object) -> None:
        """Run callback with positional arguments."""


class _FakeThread(threading.Thread):
    instances: ClassVar[list[_FakeThread]] = []

    def __init__(
        self,
        *,
        target: _Runnable,
        args: tuple[object, ...],
        name: str,
        daemon: bool,
    ) -> None:
        super().__init__(target=target, args=args, name=name, daemon=daemon)
        self._manual_target = target
        self._manual_args = args
        self.started = False
        _FakeThread.instances.append(self)

    def start(self) -> None:
        self.started = True

    def run_target(self) -> None:
        target = self._manual_target
        args = self._manual_args
        target(*args)


@dataclass(slots=True)
class _FakeView:
    prompted_path: Path | None = None
    selected_path: Path | None = None
    status_history: list[str] = field(default_factory=list)
    start_enabled_history: list[bool] = field(default_factory=list)
    presentations: list[DesktopAnalysisPresentation] = field(default_factory=list)
    chart_payloads: list[ChartDataContract] = field(default_factory=list)
    clear_chart_calls: int = 0
    errors: list[str] = field(default_factory=list)
    scheduled_callbacks: list[object] = field(default_factory=list)
    refresh_calls: int = 0
    closed: bool = False

    def prompt_csv_file(self) -> Path | None:
        return self.prompted_path

    def set_selected_path(self, path: Path) -> None:
        self.selected_path = path

    def set_status(self, value: str) -> None:
        self.status_history.append(value)

    def set_start_enabled(self, enabled: bool) -> None:
        self.start_enabled_history.append(enabled)

    def render_presentation(self, presentation: DesktopAnalysisPresentation) -> None:
        self.presentations.append(presentation)

    def render_chart(self, chart_data: ChartDataContract) -> None:
        self.chart_payloads.append(chart_data)

    def clear_chart(self) -> None:
        self.clear_chart_calls += 1

    def show_error(self, message: str) -> None:
        self.errors.append(message)

    def schedule_after(self, delay_ms: int, callback: object) -> None:
        _ = delay_ms
        self.scheduled_callbacks.append(callback)

    def refresh(self) -> None:
        self.refresh_calls += 1

    def close(self) -> None:
        self.closed = True

    def run_all_scheduled(self, max_iterations: int = 100) -> None:
        iterations = 0
        while self.scheduled_callbacks and iterations < max_iterations:
            callback = self.scheduled_callbacks.pop(0)
            assert callable(callback)
            callback()
            iterations += 1


def test_desktop_app_select_file_updates_path_and_status() -> None:
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: DesktopAnalysisPresentation(
            status="Analyse abgeschlossen",
            confidence="88%",
            result_text="result",
            forecast_text="forecast",
            projection_text="proj",
            error_text=None,
        ),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()

    assert view.selected_path == Path("C:/data/candles.csv")
    assert view.status_history[-1] == "Datei ausgewahlt. Analyse kann gestartet werden."


def test_desktop_app_select_file_cancel_keeps_previous_state() -> None:
    view = _FakeView(prompted_path=None)
    controller = DesktopAnalysisController(view=view)

    controller.on_select_file()

    assert view.selected_path is None
    assert view.status_history == []


def test_desktop_app_start_without_selected_file_shows_hint() -> None:
    view = _FakeView(prompted_path=None)
    controller = DesktopAnalysisController(view=view)

    controller.on_start_analysis()

    assert view.status_history[-1] == "Bitte zuerst eine CSV-Datei auswahlen."


def test_desktop_controller_analysis_worker_maps_domain_error_to_presentation() -> None:
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: (_ for _ in ()).throw(DomainError("invalid csv")),
    )

    controller._analysis_worker(1, Path("C:/data/candles.csv"))
    controller._poll_queue(1)

    assert view.presentations[-1].status == "Analyse fehlgeschlagen"
    assert view.presentations[-1].error_text is not None
    assert "Analyse konnte nicht ausgefuhrt werden" in view.presentations[-1].error_text


def test_desktop_controller_analysis_worker_requires_configured_analyzer() -> None:
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    controller = DesktopAnalysisController(view=view)
    controller.run_analysis_presentation = None

    with pytest.raises(RuntimeError, match="not configured"):
        controller._analysis_worker(1, Path("C:/data/candles.csv"))


def test_desktop_controller_poll_empty_queue_reschedules_while_running() -> None:
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    controller = DesktopAnalysisController(view=view)
    controller._analysis_running = True

    controller._poll_queue(3)

    assert len(view.scheduled_callbacks) == 1


def test_desktop_controller_poll_ignores_stale_run_result_and_reschedules() -> None:
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    presentation = DesktopAnalysisPresentation(
        status="Analyse abgeschlossen",
        confidence="77%",
        result_text="ready",
        forecast_text="forecast",
        projection_text="projection",
        error_text=None,
    )
    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: presentation,
    )
    controller._analysis_running = True
    controller._analysis_worker(99, Path("C:/data/candles.csv"))

    controller._poll_queue(1)

    assert view.presentations == []
    assert len(view.scheduled_callbacks) == 1


def test_desktop_controller_schedule_poll_ignored_after_close() -> None:
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    controller = DesktopAnalysisController(view=view)

    controller.on_close()
    controller._schedule_queue_poll(1)

    assert view.scheduled_callbacks == []


def test_desktop_app_run_analysis_success_updates_ui_fields() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: DesktopAnalysisPresentation(
            status="Analyse abgeschlossen",
            confidence="88%",
            result_text="result",
            forecast_text="forecast",
            projection_text="proj",
            error_text=None,
        ),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()

    assert len(_FakeThread.instances) == 1
    assert _FakeThread.instances[0].started is True
    _FakeThread.instances[0].run_target()
    view.run_all_scheduled()

    assert view.start_enabled_history == [False, True]
    assert view.presentations[-1].status == "Analyse abgeschlossen"
    assert view.clear_chart_calls == 1
    assert view.chart_payloads == []
    assert view.errors == []


def test_desktop_app_run_analysis_success_renders_chart_when_available() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    chart_data = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=(
                    ChartCandle(
                        opened_at=datetime(2026, 7, 21, 7, 0, tzinfo=UTC),
                        open_price=Decimal("100"),
                        high_price=Decimal("102"),
                        low_price=Decimal("99"),
                        close_price=Decimal("101"),
                    ),
                ),
                swings=(),
                pivots=(),
            ),
        ),
        forecast_scenarios=(
            ChartForecastScenario(
                scenario_type="primary",
                expected_next_wave="5",
                confidence=Decimal("82"),
                reasoning=("reason",),
                projection_targets=(
                    ChartProjectionTarget(
                        priority=1,
                        target_price=Decimal("110"),
                        confidence=Decimal("82"),
                        wave_degree="primary",
                        description=None,
                    ),
                ),
            ),
        ),
        fibonacci_projections=(
            ChartFibonacciProjection(
                level_ratio=Decimal("1.618"),
                price=Decimal("110"),
                direction="up",
                reference_range=Decimal("10"),
            ),
        ),
    )

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: DesktopAnalysisPresentation(
            status="Analyse abgeschlossen",
            confidence="88%",
            result_text="result",
            forecast_text="forecast",
            projection_text="proj",
            error_text=None,
            chart_data=chart_data,
        ),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()
    _FakeThread.instances[0].run_target()
    view.run_all_scheduled()

    assert view.chart_payloads == [chart_data]
    assert view.clear_chart_calls == 0


def test_desktop_app_run_analysis_error_shows_message() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: DesktopAnalysisPresentation(
            status="Analyse fehlgeschlagen",
            confidence="-",
            result_text="",
            forecast_text="",
            projection_text="",
            error_text="Boom",
        ),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()
    _FakeThread.instances[0].run_target()
    view.run_all_scheduled()

    assert view.presentations[-1].status == "Analyse fehlgeschlagen"
    assert view.errors == ["Boom"]
    assert view.clear_chart_calls == 1
    assert view.chart_payloads == []
    assert view.start_enabled_history[-1] is True


def test_desktop_app_prevents_parallel_or_double_run() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: DesktopAnalysisPresentation(
            status="Analyse abgeschlossen",
            confidence="90%",
            result_text="ok",
            forecast_text="ok",
            projection_text="ok",
            error_text=None,
        ),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()
    controller.on_start_analysis()

    assert len(_FakeThread.instances) == 1
    assert view.status_history[-1] == "Analyse laeuft bereits."


def test_desktop_app_ui_updates_happen_only_after_main_thread_poll() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    presentation = DesktopAnalysisPresentation(
        status="Analyse abgeschlossen",
        confidence="77%",
        result_text="ready",
        forecast_text="forecast",
        projection_text="projection",
        error_text=None,
    )

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: presentation,
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()
    _FakeThread.instances[0].run_target()

    assert view.presentations == []
    view.run_all_scheduled()
    assert view.presentations == [presentation]


def test_desktop_app_close_while_worker_running_suppresses_ui_updates() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: DesktopAnalysisPresentation(
            status="Analyse abgeschlossen",
            confidence="95%",
            result_text="late",
            forecast_text="late",
            projection_text="late",
            error_text=None,
        ),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()
    controller.on_close()
    _FakeThread.instances[0].run_target()
    view.run_all_scheduled()

    assert view.closed is True
    assert view.presentations == []
    assert view.errors == []


def test_desktop_controller_productive_csv_to_forecast_pipeline_remains_functional(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        """
        symbol,timeframe,opened_at,open,high,low,close,volume
        EURUSD,1h,2026-07-21T00:00:00Z,104,108,103,105,10
        EURUSD,1h,2026-07-21T01:00:00Z,101,106,100,103,10
        EURUSD,1h,2026-07-21T02:00:00Z,107,110,105,109,10
        EURUSD,1h,2026-07-21T03:00:00Z,105,107,104,106,10
        EURUSD,1h,2026-07-21T04:00:00Z,119,125,118,123,10
        EURUSD,1h,2026-07-21T05:00:00Z,117,120,116,118,10
        EURUSD,1h,2026-07-21T06:00:00Z,124,132,123,130,10
        EURUSD,1h,2026-07-21T07:00:00Z,123,128,121,126,10
        """,
    )

    presentation = present_csv_analysis(csv_path)

    assert presentation.status == "Analyse abgeschlossen"
    assert presentation.error_text is None
    assert "%" in presentation.confidence
    assert "Szenario:" in presentation.forecast_text
    assert "->" in presentation.projection_text


def test_desktop_controller_productive_csv_partial_analysis_stays_visible() -> None:
    csv_path = Path("engineering/testdata/candlestick_patterns_e2e.csv")

    presentation = present_csv_analysis(csv_path)

    assert presentation.error_text is None
    assert presentation.status == "Analyse abgeschlossen - Teilergebnisse verfuegbar"
    assert presentation.confidence == "-"
    assert "Forecast nicht verfugbar" in presentation.forecast_text
    assert "Keine Fibonacci-Projektionen" in presentation.projection_text
    assert presentation.chart_data is not None


def test_present_csv_analysis_treats_domain_error_with_forecast_text_as_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "elliottwaver.interfaces.desktop_tk.run_analysis_from_csv",
        lambda _path: (_ for _ in ()).throw(
            DomainError("analysis must be completed before forecast generation")
        ),
    )

    presentation = present_csv_analysis(Path("C:/tmp/demo.csv"))

    assert presentation.status == "Analyse fehlgeschlagen"
    assert presentation.error_text is not None


def test_desktop_app_switching_complete_to_partial_clears_stale_forecast_only() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    chart_data = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=(
                    ChartCandle(
                        opened_at=datetime(2026, 7, 21, 7, 0, tzinfo=UTC),
                        open_price=Decimal("100"),
                        high_price=Decimal("102"),
                        low_price=Decimal("99"),
                        close_price=Decimal("101"),
                    ),
                ),
                swings=(),
                pivots=(),
            ),
        ),
        forecast_scenarios=(
            ChartForecastScenario(
                scenario_type="primary",
                expected_next_wave="5",
                confidence=Decimal("82"),
                reasoning=("reason",),
                projection_targets=(
                    ChartProjectionTarget(
                        priority=1,
                        target_price=Decimal("110"),
                        confidence=Decimal("82"),
                        wave_degree="primary",
                        description=None,
                    ),
                ),
            ),
        ),
        fibonacci_projections=(
            ChartFibonacciProjection(
                level_ratio=Decimal("1.618"),
                price=Decimal("110"),
                direction="up",
                reference_range=Decimal("10"),
            ),
        ),
    )
    complete = DesktopAnalysisPresentation(
        status="Analyse abgeschlossen",
        confidence="88%",
        result_text="ok",
        forecast_text="forecast",
        projection_text="proj",
        error_text=None,
        chart_data=chart_data,
    )
    partial = DesktopAnalysisPresentation(
        status="Analyse abgeschlossen - Teilergebnisse verfuegbar",
        confidence="-",
        result_text="partial",
        forecast_text="Forecast nicht verfugbar - keine gueltige Elliott-Wellenstruktur.",
        projection_text="Keine Fibonacci-Projektionen verfugbar.",
        error_text=None,
        chart_data=chart_data,
    )
    queued = [complete, partial]

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: queued.pop(0),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()
    _FakeThread.instances[0].run_target()
    view.run_all_scheduled()

    controller.on_start_analysis()
    _FakeThread.instances[1].run_target()
    view.run_all_scheduled()

    assert len(view.presentations) == 2
    assert view.presentations[0].confidence == "88%"
    assert view.presentations[1].confidence == "-"
    assert "Forecast nicht verfugbar" in view.presentations[1].forecast_text
    assert view.clear_chart_calls == 0
    assert len(view.chart_payloads) == 2


def test_desktop_app_switching_complete_partial_complete_has_no_stale_values() -> None:
    _FakeThread.instances.clear()
    view = _FakeView(prompted_path=Path("C:/data/candles.csv"))
    chart_data = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=(
                    ChartCandle(
                        opened_at=datetime(2026, 7, 21, 7, 0, tzinfo=UTC),
                        open_price=Decimal("100"),
                        high_price=Decimal("102"),
                        low_price=Decimal("99"),
                        close_price=Decimal("101"),
                    ),
                ),
                swings=(),
                pivots=(),
            ),
        ),
        forecast_scenarios=(
            ChartForecastScenario(
                scenario_type="primary",
                expected_next_wave="5",
                confidence=Decimal("82"),
                reasoning=("reason",),
                projection_targets=(
                    ChartProjectionTarget(
                        priority=1,
                        target_price=Decimal("110"),
                        confidence=Decimal("82"),
                        wave_degree="primary",
                        description=None,
                    ),
                ),
            ),
        ),
        fibonacci_projections=(
            ChartFibonacciProjection(
                level_ratio=Decimal("1.618"),
                price=Decimal("110"),
                direction="up",
                reference_range=Decimal("10"),
            ),
        ),
    )
    complete_one = DesktopAnalysisPresentation(
        status="Analyse abgeschlossen",
        confidence="88%",
        result_text="complete-1",
        forecast_text="forecast-1",
        projection_text="proj-1",
        error_text=None,
        chart_data=chart_data,
    )
    partial = DesktopAnalysisPresentation(
        status="Analyse abgeschlossen - Teilergebnisse verfuegbar",
        confidence="-",
        result_text="partial",
        forecast_text="Forecast nicht verfugbar - keine gueltige Elliott-Wellenstruktur.",
        projection_text="Keine Fibonacci-Projektionen verfugbar.",
        error_text=None,
        chart_data=chart_data,
    )
    complete_two = DesktopAnalysisPresentation(
        status="Analyse abgeschlossen",
        confidence="91%",
        result_text="complete-2",
        forecast_text="forecast-2",
        projection_text="proj-2",
        error_text=None,
        chart_data=chart_data,
    )
    queued = [complete_one, partial, complete_two]

    controller = DesktopAnalysisController(
        view=view,
        run_analysis_presentation=lambda _path: queued.pop(0),
        thread_factory=_FakeThread,
    )

    controller.on_select_file()
    controller.on_start_analysis()
    _FakeThread.instances[0].run_target()
    view.run_all_scheduled()

    controller.on_start_analysis()
    _FakeThread.instances[1].run_target()
    view.run_all_scheduled()

    controller.on_start_analysis()
    _FakeThread.instances[2].run_target()
    view.run_all_scheduled()

    assert len(view.presentations) == 3
    assert view.presentations[0].confidence == "88%"
    assert view.presentations[1].confidence == "-"
    assert view.presentations[2].confidence == "91%"
    assert "Forecast nicht verfugbar" in view.presentations[1].forecast_text
    assert view.presentations[2].forecast_text == "forecast-2"
    assert view.presentations[2].projection_text == "proj-2"
    assert len(view.chart_payloads) == 3
    assert view.clear_chart_calls == 0


def test_present_csv_analysis_partial_path_runs_csv_and_analysis_once_and_skips_forecast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = Path("engineering/testdata/candlestick_patterns_e2e.csv")
    counters = {"read_rows": 0, "analyze": 0, "forecast": 0}
    analysis_ids: list[int] = []
    forecast_analysis_ids: list[int] = []

    original_read_rows = CsvMarketDataProvider._read_rows
    original_analyze = AnalyzeMultiTimeframeService.analyze
    original_generate = ForecastEngine.generate

    def wrapped_read_rows(self: CsvMarketDataProvider) -> tuple[tuple[int, dict[str, str]], ...]:
        counters["read_rows"] += 1
        return original_read_rows(self)

    def wrapped_analyze(
        self: AnalyzeMultiTimeframeService, request: AnalysisRequest
    ) -> AnalysisResponse:
        counters["analyze"] += 1
        result = original_analyze(self, request)
        analysis_ids.append(id(result))
        return result

    def wrapped_generate(self: ForecastEngine, analysis: AnalysisResponse | None) -> ForecastResult:
        counters["forecast"] += 1
        forecast_analysis_ids.append(id(analysis))
        return original_generate(self, analysis)

    monkeypatch.setattr(CsvMarketDataProvider, "_read_rows", wrapped_read_rows)
    monkeypatch.setattr(AnalyzeMultiTimeframeService, "analyze", wrapped_analyze)
    monkeypatch.setattr(ForecastEngine, "generate", wrapped_generate)

    presentation = present_csv_analysis(csv_path)

    assert counters == {"read_rows": 1, "analyze": 1, "forecast": 0}
    assert analysis_ids != []
    assert forecast_analysis_ids == []
    assert presentation.status == "Analyse abgeschlossen - Teilergebnisse verfuegbar"
    assert presentation.error_text is None
    assert presentation.chart_data is not None
    assert "Stage: confluence" in presentation.result_text
    assert presentation.confidence == "-"
    assert "Forecast nicht verfugbar" in presentation.forecast_text
    assert "Keine Fibonacci-Projektionen" in presentation.projection_text


def test_present_csv_analysis_complete_path_runs_csv_analysis_and_forecast_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = Path("engineering/testdata/swing_e2e_100.csv")
    counters = {"read_rows": 0, "analyze": 0, "forecast": 0}
    analysis_ids: list[int] = []
    forecast_analysis_ids: list[int] = []

    original_read_rows = CsvMarketDataProvider._read_rows
    original_analyze = AnalyzeMultiTimeframeService.analyze
    original_generate = ForecastEngine.generate

    def wrapped_read_rows(self: CsvMarketDataProvider) -> tuple[tuple[int, dict[str, str]], ...]:
        counters["read_rows"] += 1
        return original_read_rows(self)

    def wrapped_analyze(
        self: AnalyzeMultiTimeframeService, request: AnalysisRequest
    ) -> AnalysisResponse:
        counters["analyze"] += 1
        result = original_analyze(self, request)
        analysis_ids.append(id(result))
        return result

    def wrapped_generate(self: ForecastEngine, analysis: AnalysisResponse | None) -> ForecastResult:
        counters["forecast"] += 1
        forecast_analysis_ids.append(id(analysis))
        return original_generate(self, analysis)

    monkeypatch.setattr(CsvMarketDataProvider, "_read_rows", wrapped_read_rows)
    monkeypatch.setattr(AnalyzeMultiTimeframeService, "analyze", wrapped_analyze)
    monkeypatch.setattr(ForecastEngine, "generate", wrapped_generate)

    presentation = present_csv_analysis(csv_path)

    assert counters == {"read_rows": 1, "analyze": 1, "forecast": 1}
    assert len(analysis_ids) == 1
    assert forecast_analysis_ids == analysis_ids
    assert presentation.status == "Analyse abgeschlossen"
    assert presentation.error_text is None
    assert presentation.chart_data is not None
    assert "%" in presentation.confidence
    assert "Szenario:" in presentation.forecast_text


def test_present_csv_analysis_unexpected_forecast_domain_error_is_not_masked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_generate = ForecastEngine.generate

    def wrapped_generate(self: ForecastEngine, analysis: AnalysisResponse | None) -> ForecastResult:
        _ = self
        _ = analysis
        message = "unexpected forecast failure"
        raise DomainError(message)

    monkeypatch.setattr(ForecastEngine, "generate", wrapped_generate)

    presentation = present_csv_analysis(Path("engineering/testdata/swing_e2e_100.csv"))

    assert presentation.status == "Analyse fehlgeschlagen"
    assert presentation.error_text is not None
    assert "Analyse konnte nicht ausgefuhrt werden" in presentation.error_text

    monkeypatch.setattr(ForecastEngine, "generate", original_generate)


def test_analysis_desktop_tk_app_methods_and_dialog_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tk.Tk()
    root.withdraw()

    class _ControllerStub:
        def __init__(self) -> None:
            self.closed = False

        def on_close(self) -> None:
            self.closed = True

        def on_start_analysis(self) -> None:
            return

        def on_select_file(self) -> None:
            return

    controller_stub = _ControllerStub()

    def _controller_factory(*, view: object) -> _ControllerStub:
        _ = view
        return controller_stub

    monkeypatch.setattr(
        "elliottwaver.interfaces.desktop_tk.DesktopAnalysisController",
        _controller_factory,
    )

    errors: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "elliottwaver.interfaces.desktop_tk.messagebox.showerror",
        lambda title, message: errors.append((title, message)),
    )

    try:
        app = AnalysisDesktopTkApp(root)

        monkeypatch.setattr(
            "elliottwaver.interfaces.desktop_tk.filedialog.askopenfilename",
            lambda **_kwargs: "C:/data/candles.csv",
        )
        assert app.prompt_csv_file() == Path("C:/data/candles.csv")

        monkeypatch.setattr(
            "elliottwaver.interfaces.desktop_tk.filedialog.askopenfilename",
            lambda **_kwargs: "",
        )
        assert app.prompt_csv_file() is None

        app.set_selected_path(Path("C:/tmp/demo.csv"))
        app.set_status("running")
        app.set_start_enabled(False)
        app.set_start_enabled(True)

        presentation = DesktopAnalysisPresentation(
            status="Analyse abgeschlossen",
            confidence="88%",
            result_text="summary",
            forecast_text="forecast",
            projection_text="projection",
            error_text=None,
        )
        app.render_presentation(presentation)

        assert app._status_var.get() == "Analyse abgeschlossen"
        assert app._confidence_var.get() == "88%"
        assert "summary" in app._result_text.get("1.0", tk.END)
        pane_names = tuple(
            str(name)
            for name in app._content_pane.tk.splitlist(
                app._content_pane.tk.call(str(app._content_pane), "panes")
            )
        )
        assert len(pane_names) == 2
        assert app._chart_view.master in {root.nametowidget(name) for name in pane_names}

        called: list[str] = []
        app.schedule_after(0, lambda: called.append("scheduled"))
        root.update()
        assert called == ["scheduled"]

        app.show_error("boom")
        assert errors == [("Analysefehler", "boom")]

        app.close()
    finally:
        with suppress(tk.TclError):
            root.destroy()


def test_launch_analysis_desktop_builds_app_and_runs_mainloop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RootStub:
        def __init__(self) -> None:
            self.mainloop_calls = 0

        def mainloop(self) -> None:
            self.mainloop_calls += 1

    root = _RootStub()
    app_roots: list[object] = []

    def _capture_app_root(_root_arg: object) -> None:
        app_roots.append(_root_arg)

    monkeypatch.setattr("elliottwaver.interfaces.desktop_tk.tk.Tk", lambda: root)
    monkeypatch.setattr(
        "elliottwaver.interfaces.desktop_tk.AnalysisDesktopTkApp",
        _capture_app_root,
    )

    launch_analysis_desktop()

    assert app_roots == [root]
    assert root.mainloop_calls == 1
