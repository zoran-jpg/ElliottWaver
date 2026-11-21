"""Minimal tkinter desktop interface for running analysis workflows."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING, Protocol

from elliottwaver.application import (
    AnalysisApplicationResult,
    AnalysisRequest,
    ChartDataContract,
    TimeframeAnalysisRequest,
    build_chart_data_contract,
)
from elliottwaver.bootstrap import build_csv_analysis_application
from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.infrastructure.market_data import CsvMarketDataProvider
from elliottwaver.interfaces.chart_tk import CandlestickChartView

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime


class DesktopAnalysisView(Protocol):
    """UI contract consumed by the desktop analysis controller."""

    def prompt_csv_file(self) -> Path | None:
        """Prompt the user to pick a CSV file."""

    def set_selected_path(self, path: Path) -> None:
        """Display the currently selected CSV path."""

    def set_status(self, value: str) -> None:
        """Display status information."""

    def set_start_enabled(self, enabled: bool) -> None:
        """Enable or disable the analysis start action."""

    def render_presentation(self, presentation: DesktopAnalysisPresentation) -> None:
        """Render a completed presentation payload."""

    def render_chart(self, chart_data: ChartDataContract) -> None:
        """Render chart data for the selected analysis timeframe."""

    def clear_chart(self) -> None:
        """Clear chart output when no chart data is available."""

    def show_error(self, message: str) -> None:
        """Display an error dialog."""

    def schedule_after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        """Schedule a callback on the UI main thread."""

    def refresh(self) -> None:
        """Flush immediate visual state updates."""

    def close(self) -> None:
        """Close the underlying UI window."""


_POLL_INTERVAL_MS = 50


@dataclass(frozen=True, slots=True)
class CsvAnalysisRequestSpec:
    """Input request values derived from a candle CSV file."""

    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True)
class DesktopAnalysisPresentation:
    """UI-ready representation of one desktop analysis attempt."""

    status: str
    confidence: str
    result_text: str
    forecast_text: str
    projection_text: str
    error_text: str | None = None
    chart_data: ChartDataContract | None = None


@dataclass(frozen=True, slots=True)
class _AnalysisWorkerResult:
    """Thread-safe payload transferred from worker to UI thread."""

    run_id: int
    presentation: DesktopAnalysisPresentation


@dataclass(slots=True)
class DesktopAnalysisController:
    """Orchestrates desktop analysis without touching Tk widgets from workers."""

    view: DesktopAnalysisView
    run_analysis_presentation: Callable[[Path], DesktopAnalysisPresentation] | None = None
    thread_factory: Callable[..., threading.Thread] = threading.Thread
    poll_interval_ms: int = _POLL_INTERVAL_MS
    _selected_path: Path | None = field(init=False, default=None)
    _analysis_running: bool = field(init=False, default=False)
    _is_closing: bool = field(init=False, default=False)
    _run_id: int = field(init=False, default=0)
    _result_queue: queue.Queue[_AnalysisWorkerResult] = field(
        init=False,
        default_factory=queue.Queue,
    )
    _worker_thread: threading.Thread | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.run_analysis_presentation is None:
            self.run_analysis_presentation = present_csv_analysis

    def on_select_file(self) -> None:
        selected = self.view.prompt_csv_file()
        if selected is None:
            return

        self._selected_path = selected
        self.view.set_selected_path(selected)
        self.view.set_status("Datei ausgewahlt. Analyse kann gestartet werden.")

    def on_start_analysis(self) -> None:
        if self._selected_path is None:
            self.view.set_status("Bitte zuerst eine CSV-Datei auswahlen.")
            return

        if self._analysis_running:
            self.view.set_status("Analyse laeuft bereits.")
            return

        self._analysis_running = True
        self._run_id += 1
        active_run_id = self._run_id
        self.view.set_status("Analyse lauft...")
        self.view.set_start_enabled(False)
        self.view.refresh()

        selected_path = self._selected_path
        self._worker_thread = self.thread_factory(
            target=self._analysis_worker,
            args=(active_run_id, selected_path),
            name=f"analysis-worker-{active_run_id}",
            daemon=True,
        )
        self._worker_thread.start()
        self._schedule_queue_poll(active_run_id)

    def on_close(self) -> None:
        self._is_closing = True
        self._analysis_running = False
        self.view.close()

    def _analysis_worker(self, run_id: int, csv_path: Path) -> None:
        analyzer = self.run_analysis_presentation
        if analyzer is None:
            message = "run_analysis_presentation is not configured"
            raise RuntimeError(message)

        try:
            presentation = analyzer(csv_path)
        except (DomainError, OSError, ValueError) as error:
            presentation = DesktopAnalysisPresentation(
                status="Analyse fehlgeschlagen",
                confidence="-",
                result_text="",
                forecast_text="",
                projection_text="",
                error_text=human_readable_error(error),
            )

        self._result_queue.put(
            _AnalysisWorkerResult(
                run_id=run_id,
                presentation=presentation,
            )
        )

    def _schedule_queue_poll(self, run_id: int) -> None:
        if self._is_closing:
            return
        self.view.schedule_after(self.poll_interval_ms, lambda: self._poll_queue(run_id))

    def _poll_queue(self, run_id: int) -> None:
        if self._is_closing:
            return

        try:
            result = self._result_queue.get_nowait()
        except queue.Empty:
            if self._analysis_running:
                self._schedule_queue_poll(run_id)
            return

        if result.run_id != run_id:
            if self._analysis_running:
                self._schedule_queue_poll(run_id)
            return

        self._analysis_running = False
        self._worker_thread = None
        self._apply_presentation(result.presentation)

    def _apply_presentation(self, presentation: DesktopAnalysisPresentation) -> None:
        if self._is_closing:
            return

        self.view.render_presentation(presentation)
        if presentation.chart_data is None:
            self.view.clear_chart()
        else:
            self.view.render_chart(presentation.chart_data)

        if presentation.error_text is not None:
            self.view.show_error(presentation.error_text)

        self.view.set_start_enabled(True)


class AnalysisDesktopTkApp:
    """Simple desktop UI around AnalysisApplication."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._root.title("ElliottWaver - MVP Analysis")
        self._root.geometry("940x640")
        self._root.minsize(900, 640)

        self._status_var = tk.StringVar(value="Bereit")
        self._path_var = tk.StringVar(value="Keine Datei ausgewahlt")
        self._confidence_var = tk.StringVar(value="-")
        self._controller = DesktopAnalysisController(view=self)
        self._root.protocol("WM_DELETE_WINDOW", self._controller.on_close)

        self._build_layout()

    def _build_layout(self) -> None:
        frame = ttk.Frame(self._root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(4, weight=1)

        ttk.Label(frame, text="CSV-Datei:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self._path_var, state="readonly").grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(8, 8),
        )
        ttk.Button(frame, text="Datei auswahlen", command=self._select_file).grid(
            row=0,
            column=2,
            sticky="ew",
        )

        self._analyze_button = ttk.Button(
            frame,
            text="Analyse starten",
            command=self._controller.on_start_analysis,
        )
        self._analyze_button.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(10, 10),
        )

        ttk.Label(frame, text="Status:").grid(row=2, column=0, sticky="w")
        ttk.Label(frame, textvariable=self._status_var).grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="w",
            padx=(8, 0),
        )

        ttk.Label(frame, text="Confidence:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(frame, textvariable=self._confidence_var).grid(
            row=3,
            column=1,
            columnspan=2,
            sticky="w",
            padx=(8, 0),
            pady=(8, 0),
        )

        self._content_pane = ttk.Panedwindow(frame, orient=tk.VERTICAL)
        self._content_pane.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        analysis_panel = ttk.Frame(self._content_pane)
        analysis_panel.columnconfigure(0, weight=1)
        analysis_panel.rowconfigure(1, weight=1)
        analysis_panel.rowconfigure(3, weight=1)
        analysis_panel.rowconfigure(5, weight=1)

        ttk.Label(analysis_panel, text="Ergebnis:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._result_text = tk.Text(analysis_panel, height=6, wrap="word", state="disabled")
        self._result_text.grid(row=1, column=0, sticky="nsew")

        ttk.Label(analysis_panel, text="Forecast:").grid(row=2, column=0, sticky="w", pady=(10, 4))
        self._forecast_text = tk.Text(analysis_panel, height=7, wrap="word", state="disabled")
        self._forecast_text.grid(row=3, column=0, sticky="nsew")

        ttk.Label(analysis_panel, text="Fibonacci-Projektionen:").grid(
            row=4,
            column=0,
            sticky="w",
            pady=(10, 4),
        )
        self._projection_text = tk.Text(analysis_panel, height=6, wrap="word", state="disabled")
        self._projection_text.grid(row=5, column=0, sticky="nsew")

        chart_panel = ttk.Frame(self._content_pane)
        chart_panel.columnconfigure(0, weight=1)
        chart_panel.rowconfigure(1, weight=1)

        ttk.Label(chart_panel, text="Candlestick-Chart:").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self._chart_view = CandlestickChartView(chart_panel)
        self._chart_view.grid(row=1, column=0, sticky="nsew")

        self._content_pane.add(analysis_panel, weight=3)
        self._content_pane.add(chart_panel, weight=2)

    def _select_file(self) -> None:
        self._controller.on_select_file()

    def prompt_csv_file(self) -> Path | None:
        selected = filedialog.askopenfilename(
            title="CSV fur Analyse auswahlen",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not selected:
            return None
        return Path(selected)

    def set_selected_path(self, path: Path) -> None:
        self._path_var.set(str(path))

    def set_status(self, value: str) -> None:
        self._status_var.set(value)

    def set_start_enabled(self, enabled: bool) -> None:
        if enabled:
            self._analyze_button.state(["!disabled"])
            return
        self._analyze_button.state(["disabled"])

    def render_presentation(self, presentation: DesktopAnalysisPresentation) -> None:
        self._status_var.set(presentation.status)
        self._confidence_var.set(presentation.confidence)
        self._set_text(self._result_text, presentation.result_text)
        self._set_text(self._forecast_text, presentation.forecast_text)
        self._set_text(self._projection_text, presentation.projection_text)

    def show_error(self, message: str) -> None:
        messagebox.showerror("Analysefehler", message)

    def render_chart(self, chart_data: ChartDataContract) -> None:
        self._chart_view.render_contract(chart_data)

    def clear_chart(self) -> None:
        self._chart_view.clear()

    def schedule_after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        self._root.after(delay_ms, callback)

    def refresh(self) -> None:
        self._root.update_idletasks()

    def close(self) -> None:
        self._root.destroy()

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.config(state="disabled")


def infer_request_spec_from_csv(csv_path: Path) -> CsvAnalysisRequestSpec:
    """Infer a minimal analysis request from CSV metadata columns."""
    provider = CsvMarketDataProvider(csv_path=csv_path)
    spec = provider.infer_request_spec()

    return CsvAnalysisRequestSpec(
        symbol=spec.symbol.value,
        timeframe=spec.timeframe.value,
        start_time=spec.start_time,
        end_time=spec.end_time,
    )


def run_analysis_from_csv(csv_path: Path) -> AnalysisApplicationResult:
    """Run analysis and forecast for one CSV file using AnalysisApplication only."""

    spec = infer_request_spec_from_csv(csv_path)
    app = build_csv_analysis_application(csv_path=csv_path)
    request = build_analysis_request(spec)
    return app.run(request)


def present_csv_analysis(csv_path: Path) -> DesktopAnalysisPresentation:
    """Run the CSV analysis flow and return a UI-ready presentation model."""

    try:
        result = run_analysis_from_csv(csv_path)
    except (DomainError, OSError, ValueError) as error:
        message = human_readable_error(error)
        return DesktopAnalysisPresentation(
            status="Analyse fehlgeschlagen",
            confidence="-",
            result_text="",
            forecast_text="",
            projection_text="",
            error_text=message,
        )

    result_text = format_analysis_overview(result)
    confidence_text, forecast_text, projection_text = format_analysis_result(result)
    try:
        chart_data = build_chart_data_contract(result)
    except (DomainError, OSError, ValueError):
        chart_data = None
    return DesktopAnalysisPresentation(
        status="Analyse abgeschlossen",
        confidence=confidence_text,
        result_text=result_text,
        forecast_text=forecast_text,
        projection_text=projection_text,
        error_text=None,
        chart_data=chart_data,
    )


def build_analysis_request(spec: CsvAnalysisRequestSpec) -> AnalysisRequest:
    """Build an AnalysisRequest from inferred CSV metadata."""

    symbol = Symbol(spec.symbol)
    timeframe = MarketTimeframe.parse(spec.timeframe)
    timeframe_request = TimeframeAnalysisRequest(
        symbol=symbol,
        timeframe=timeframe,
        start_time=spec.start_time,
        end_time=spec.end_time,
    )
    return AnalysisRequest(
        symbol=symbol,
        timeframe_requests=(timeframe_request,),
        start_time=spec.start_time,
        end_time=spec.end_time,
    )


def format_analysis_result(result: AnalysisApplicationResult) -> tuple[str, str, str]:
    """Build display strings for confidence, forecast, and projections."""

    forecast = result.forecast

    confidence_text = "-"
    if forecast.primary_scenario is not None:
        confidence_text = f"{forecast.overall_confidence}%"

    if forecast.primary_scenario is None:
        forecast_text = "Kein Forecast verfugbar."
    else:
        lines = [
            f"Szenario: {forecast.primary_scenario.scenario_type.value}",
            f"Erwartete Welle: {forecast.primary_scenario.expected_next_wave}",
        ]
        lines.extend(f"- {entry}" for entry in forecast.primary_scenario.reasoning)
        if forecast.alternative_scenarios:
            lines.append("")
            lines.append("Alternative Szenarien:")
            lines.extend(
                f"- {scenario.scenario_type.value}: {scenario.expected_next_wave}"
                for scenario in forecast.alternative_scenarios
            )
        forecast_text = "\n".join(lines)

    if not forecast.projections:
        projection_text = "Keine Fibonacci-Projektionen verfugbar."
    else:
        projection_text = "\n".join(
            f"{projection.level.ratio} -> {projection.price.value} ({projection.direction.value})"
            for projection in forecast.projections
        )

    return confidence_text, forecast_text, projection_text


def format_analysis_overview(result: AnalysisApplicationResult) -> str:
    """Build a compact analysis summary for the desktop result area."""

    analysis = result.analysis
    lines = [
        f"Stage: {analysis.stage.value}",
        f"Symbol: {analysis.metadata.symbol.value}",
        "Timeframes angefragt: "
        + ", ".join(timeframe.value for timeframe in analysis.metadata.requested_timeframes),
        "Timeframes verarbeitet: "
        + (
            ", ".join(timeframe.value for timeframe in analysis.metadata.processed_timeframes)
            if analysis.metadata.processed_timeframes
            else "-"
        ),
    ]

    if analysis.issues:
        lines.append("Issues:")
        lines.extend(f"- {issue.issue_code}: {issue.message}" for issue in analysis.issues)
    else:
        lines.append("Issues: keine")

    return "\n".join(lines)


def human_readable_error(error: Exception) -> str:
    """Map low-level failures to concise user-facing error text."""

    details = str(error)
    if "analysis must be completed before forecast generation" in details:
        return (
            "Analyse lieferte noch keinen abgeschlossenen Forecast. "
            "Bitte CSV-Daten und Timeframe prufen oder mit vollstandigem "
            "Swing-Input erneut starten."
        )

    return (
        "Analyse konnte nicht ausgefuhrt werden. "
        f"Details: {error}. Bitte CSV-Format, Symbol, Timeframe und UTC-Zeitstempel prufen."
    )


def launch_analysis_desktop() -> None:
    """Start the tkinter desktop UI."""

    root = tk.Tk()
    AnalysisDesktopTkApp(root)
    root.mainloop()
