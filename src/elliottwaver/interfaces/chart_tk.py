"""Tkinter candlestick chart view and deterministic render planning."""

from __future__ import annotations

import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from itertools import pairwise
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from elliottwaver.application.chart_contract import (
        ChartCandle,
        ChartCandlestickPattern,
        ChartDataContract,
        ChartFibonacciProjection,
        ChartForecastScenario,
        ChartPivot,
        ChartSupportResistanceZone,
        ChartSwing,
        ChartWave,
        TimeframeChartData,
    )


_MARGIN_LEFT = 56
_MARGIN_RIGHT = 16
_MARGIN_TOP = 16
_MARGIN_BOTTOM = 28
_MIN_VISIBLE_CANDLES = 8
_DEFAULT_VISIBLE_CANDLES = 64
_MIN_WAVE_ANCHORS = 2
_DEFAULT_VISIBLE_SUPPORT_ZONES = 3
_DEFAULT_VISIBLE_RESISTANCE_ZONES = 3
_MAX_VISIBLE_ZONE_LIMIT = 5
_SHOW_ZONE_LABELS_DEFAULT = False
_ZONE_LABEL_MIN_VERTICAL_GAP = 14.0
_ZONE_LABEL_MIN_HEIGHT = 3.0
_ZONE_VISUAL_MIN_GAP_PIXELS = 6.0
_ZONE_STRONG_OVERLAP_RATIO = 0.6
_DEFAULT_VISIBLE_PATTERN_MARKERS = 12
_PATTERN_LABEL_MIN_X_GAP = 22.0


@dataclass(frozen=True, slots=True)
class CandlestickPrimitive:
    """Screen-space primitive describing one candle body and wick."""

    opened_at: datetime
    x_center: float
    wick_top: float
    wick_bottom: float
    body_top: float
    body_bottom: float
    body_left: float
    body_right: float
    bullish: bool


@dataclass(frozen=True, slots=True)
class AxisLabel:
    """Axis label coordinates and content."""

    x: float
    y: float
    text: str


@dataclass(frozen=True, slots=True)
class ChartRenderModel:
    """Deterministic plan for rendering candles and axes."""

    candles: tuple[ChartCandle, ...]
    primitives: tuple[CandlestickPrimitive, ...]
    swing_lines: tuple[SwingLinePrimitive, ...]
    swing_markers: tuple[SwingMarkerPrimitive, ...]
    pivot_markers: tuple[PivotMarkerPrimitive, ...]
    support_resistance_zones: tuple[SupportResistanceZonePrimitive, ...]
    candlestick_patterns: tuple[CandlestickPatternPrimitive, ...]
    wave_lines: tuple[WaveLinePrimitive, ...]
    wave_labels: tuple[WaveLabelPrimitive, ...]
    fibonacci_lines: tuple[FibonacciLinePrimitive, ...]
    scenario_labels: tuple[AxisLabel, ...]
    time_labels: tuple[AxisLabel, ...]
    price_labels: tuple[AxisLabel, ...]
    min_price: Decimal
    max_price: Decimal


@dataclass(frozen=True, slots=True)
class PivotMarkerPrimitive:
    """Overlay marker for one pivot point."""

    pivot_id: str
    timestamp: datetime
    pivot_type: str
    x: float
    y: float
    confirmed: bool


@dataclass(frozen=True, slots=True)
class SwingMarkerPrimitive:
    """Overlay marker for confirmed swing highs and lows."""

    pivot_id: str
    timestamp: datetime
    marker_type: str
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class SwingLinePrimitive:
    """Overlay line connecting consecutive confirmed swing points."""

    start_pivot_id: str
    end_pivot_id: str
    start_timestamp: datetime
    end_timestamp: datetime
    x1: float
    y1: float
    x2: float
    y2: float
    direction: str


@dataclass(frozen=True, slots=True)
class WaveLinePrimitive:
    """Overlay line segment for selected Elliott wave anchors."""

    wave_id: str
    selection_rank: int
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True, slots=True)
class WaveLabelPrimitive:
    """Text label for wave anchors and wave degree markers."""

    wave_id: str
    selection_rank: int
    x: float
    y: float
    text: str


@dataclass(frozen=True, slots=True)
class FibonacciLinePrimitive:
    """Horizontal fibonacci target line with ratio/price label."""

    ratio: Decimal
    price: Decimal
    y: float
    x_start: float
    x_end: float
    label: str


@dataclass(frozen=True, slots=True)
class SupportResistanceZonePrimitive:
    """Horizontal support/resistance zone band rendered across the plot area."""

    zone_type: str
    y_top: float
    y_bottom: float
    x_start: float
    x_end: float
    touch_count: int
    label: str | None


@dataclass(frozen=True, slots=True)
class CandlestickPatternPrimitive:
    """Chart marker for one or more candlestick patterns ending on the same candle."""

    ended_at: datetime
    x: float
    y: float
    label: str
    color: str


@dataclass(frozen=True, slots=True)
class _ZoneRelevanceScore:
    zone: ChartSupportResistanceZone
    touch_score: int
    recency_score: float
    proximity_score: float

    @property
    def total_score(self) -> float:
        return self.touch_score + self.recency_score + self.proximity_score


@dataclass(frozen=True, slots=True)
class ChartViewport:
    """Visible chart window over a full candle sequence."""

    start_index: int
    visible_count: int
    total_candles: int

    @classmethod
    def initial(
        cls, total_candles: int, visible_count: int = _DEFAULT_VISIBLE_CANDLES
    ) -> ChartViewport:
        """Create a viewport anchored at the latest candles."""

        resolved_visible = _clamp_visible(visible_count, total_candles)
        resolved_start = max(total_candles - resolved_visible, 0)
        return cls(
            start_index=resolved_start,
            visible_count=resolved_visible,
            total_candles=total_candles,
        )

    def pan(self, steps: int) -> ChartViewport:
        """Move viewport left (negative) or right (positive) without changing zoom."""

        if self.total_candles == 0:
            return self

        max_start = max(self.total_candles - self.visible_count, 0)
        next_start = min(max(self.start_index + steps, 0), max_start)
        return ChartViewport(
            start_index=next_start,
            visible_count=self.visible_count,
            total_candles=self.total_candles,
        )

    def zoom(self, delta: int) -> ChartViewport:
        """Change visible candle count while preserving the right edge when possible."""

        if self.total_candles == 0:
            return self

        target_visible = _clamp_visible(self.visible_count + delta, self.total_candles)
        right_edge = self.start_index + self.visible_count
        next_start = max(right_edge - target_visible, 0)
        max_start = max(self.total_candles - target_visible, 0)
        next_start = min(next_start, max_start)
        return ChartViewport(
            start_index=next_start,
            visible_count=target_visible,
            total_candles=self.total_candles,
        )


class CandlestickChartView(ttk.Frame):
    """Tk chart widget that renders candlesticks from CHART-001 contract data."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)

        self._canvas = tk.Canvas(self, background="#10141c", highlightthickness=0)
        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(controls, text="<", width=3, command=self.pan_left).grid(row=0, column=0)
        ttk.Button(controls, text=">", width=3, command=self.pan_right).grid(
            row=0, column=1, padx=(4, 0)
        )
        ttk.Button(controls, text="+", width=3, command=self.zoom_in).grid(
            row=0, column=2, padx=(10, 0)
        )
        ttk.Button(controls, text="-", width=3, command=self.zoom_out).grid(
            row=0, column=3, padx=(4, 0)
        )
        ttk.Button(controls, text="Reset", command=self.reset_view).grid(
            row=0, column=4, padx=(10, 0)
        )
        self._show_support_resistance_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="S/R Zonen",
            variable=self._show_support_resistance_var,
            command=self._render,
        ).grid(row=0, column=5, padx=(10, 0))
        self._show_candlestick_patterns_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="Kerzenformationen",
            variable=self._show_candlestick_patterns_var,
            command=self._render,
        ).grid(row=0, column=6, padx=(10, 0))

        self._canvas.grid(row=1, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._contract: ChartDataContract | None = None
        self._timeframe_index = 0
        self._viewport = ChartViewport.initial(0)

        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mouse_wheel)

    def render_contract(self, contract: ChartDataContract) -> None:
        """Render chart data for the currently selected timeframe."""

        _ensure_main_thread()
        self._contract = contract
        self._timeframe_index = 0
        candles = self._active_candles()
        self._viewport = ChartViewport.initial(len(candles))
        self._render()

    def clear(self) -> None:
        """Clear chart content and reset viewport state."""

        _ensure_main_thread()
        self._contract = None
        self._viewport = ChartViewport.initial(0)
        self._canvas.delete("all")

    def reset_view(self) -> None:
        """Reset chart zoom and pan to default state."""

        _ensure_main_thread()
        candles = self._active_candles()
        self._viewport = ChartViewport.initial(len(candles))
        self._render()

    def zoom_in(self) -> None:
        """Show fewer candles."""

        _ensure_main_thread()
        self._viewport = self._viewport.zoom(-max(1, self._viewport.visible_count // 5))
        self._render()

    def zoom_out(self) -> None:
        """Show more candles."""

        _ensure_main_thread()
        self._viewport = self._viewport.zoom(max(1, self._viewport.visible_count // 5))
        self._render()

    def pan_left(self) -> None:
        """Move viewport to older candles."""

        _ensure_main_thread()
        self._viewport = self._viewport.pan(-max(1, self._viewport.visible_count // 5))
        self._render()

    def pan_right(self) -> None:
        """Move viewport to newer candles."""

        _ensure_main_thread()
        self._viewport = self._viewport.pan(max(1, self._viewport.visible_count // 5))
        self._render()

    def _active_candles(self) -> tuple[ChartCandle, ...]:
        timeframe_data = self._active_timeframe_data()
        if timeframe_data is None:
            return ()
        return timeframe_data.candles

    def _active_timeframe_data(self) -> TimeframeChartData | None:
        if self._contract is None or not self._contract.timeframe_data:
            return None
        return self._contract.timeframe_data[self._timeframe_index]

    def _render(self) -> None:
        timeframe_data = self._active_timeframe_data()
        candles = () if timeframe_data is None else timeframe_data.candles
        self._canvas.delete("all")

        if not candles:
            self._canvas.create_text(
                12,
                12,
                anchor="nw",
                fill="#c5cedd",
                text="Keine Chart-Daten verfuegbar.",
            )
            return

        width = max(self._canvas.winfo_width(), 200)
        height = max(self._canvas.winfo_height(), 140)
        model = build_chart_render_model(
            candles=candles,
            width=width,
            height=height,
            viewport=self._viewport,
            swings=() if timeframe_data is None else timeframe_data.swings,
            pivots=() if timeframe_data is None else timeframe_data.pivots,
            selected_waves=() if timeframe_data is None else timeframe_data.selected_waves,
            support_resistance_zones=()
            if timeframe_data is None or not self._show_support_resistance_enabled()
            else timeframe_data.support_resistance_zones,
            candlestick_patterns=()
            if timeframe_data is None or not self._show_candlestick_patterns_enabled()
            else timeframe_data.candlestick_patterns,
            forecast_scenarios=() if self._contract is None else self._contract.forecast_scenarios,
            fibonacci_projections=()
            if self._contract is None
            else self._contract.fibonacci_projections,
        )

        self._draw_axes(width=width, height=height)
        self._draw_support_resistance_overlays(model.support_resistance_zones)
        self._draw_candles(model.primitives)
        self._draw_candlestick_pattern_overlays(model.candlestick_patterns)
        self._draw_candlestick_pattern_status_hint(
            () if timeframe_data is None else timeframe_data.candlestick_patterns
        )
        self._draw_swing_overlays(model.swing_lines, model.pivot_markers, model.swing_markers)
        self._draw_wave_overlays(model.wave_lines, model.wave_labels)
        self._draw_fibonacci_overlays(model.fibonacci_lines)
        self._draw_axis_and_scenario_labels(
            model.time_labels,
            model.price_labels,
            model.scenario_labels,
        )

    def _draw_candles(self, primitives: tuple[CandlestickPrimitive, ...]) -> None:
        for candle_primitive in primitives:
            self._canvas.create_line(
                candle_primitive.x_center,
                candle_primitive.wick_top,
                candle_primitive.x_center,
                candle_primitive.wick_bottom,
                fill="#d8dee9",
                width=1,
            )
            fill = "#00b27a" if candle_primitive.bullish else "#e04f5f"
            self._canvas.create_rectangle(
                candle_primitive.body_left,
                candle_primitive.body_top,
                candle_primitive.body_right,
                candle_primitive.body_bottom,
                fill=fill,
                outline=fill,
            )

    def _draw_swing_overlays(
        self,
        swing_lines: tuple[SwingLinePrimitive, ...],
        pivot_markers: tuple[PivotMarkerPrimitive, ...],
        swing_markers: tuple[SwingMarkerPrimitive, ...],
    ) -> None:
        for swing_line in swing_lines:
            self._canvas.create_line(
                swing_line.x1,
                swing_line.y1,
                swing_line.x2,
                swing_line.y2,
                fill="#f0c674",
                width=2,
            )

        for pivot_marker in pivot_markers:
            radius = 3.0
            fill = "" if not pivot_marker.confirmed else "#8aa0b8"
            outline = "#f4c95d" if not pivot_marker.confirmed else "#8aa0b8"
            self._canvas.create_oval(
                pivot_marker.x - radius,
                pivot_marker.y - radius,
                pivot_marker.x + radius,
                pivot_marker.y + radius,
                fill=fill,
                outline=outline,
                width=1,
            )

        for swing_marker in swing_markers:
            size = 6.0
            if swing_marker.marker_type == "high":
                points = (
                    swing_marker.x,
                    swing_marker.y - size,
                    swing_marker.x - size,
                    swing_marker.y + size,
                    swing_marker.x + size,
                    swing_marker.y + size,
                )
                fill = "#ff8c69"
            else:
                points = (
                    swing_marker.x,
                    swing_marker.y + size,
                    swing_marker.x - size,
                    swing_marker.y - size,
                    swing_marker.x + size,
                    swing_marker.y - size,
                )
                fill = "#4ecdc4"
            self._canvas.create_polygon(*points, fill=fill, outline=fill)

    def _draw_wave_overlays(
        self,
        wave_lines: tuple[WaveLinePrimitive, ...],
        wave_labels: tuple[WaveLabelPrimitive, ...],
    ) -> None:
        for wave_line in wave_lines:
            color = "#6bc1ff" if wave_line.selection_rank == 1 else "#9d84ff"
            self._canvas.create_line(
                wave_line.x1,
                wave_line.y1,
                wave_line.x2,
                wave_line.y2,
                fill=color,
                width=2,
                dash=(6, 3),
            )

        for wave_label in wave_labels:
            color = "#8fd3ff" if wave_label.selection_rank == 1 else "#c0adff"
            self._canvas.create_text(
                wave_label.x,
                wave_label.y,
                text=wave_label.text,
                fill=color,
                anchor="s",
            )

    def _draw_support_resistance_overlays(
        self,
        zones: tuple[SupportResistanceZonePrimitive, ...],
    ) -> None:
        last_label_y: float | None = None
        for zone in zones:
            if zone.zone_type == "support":
                fill = "#4bbfbf"
                outline = "#5ad1d1"
            else:
                fill = "#e2a35e"
                outline = "#f1bd83"

            self._canvas.create_rectangle(
                zone.x_start,
                zone.y_top,
                zone.x_end,
                zone.y_bottom,
                fill=fill,
                outline=outline,
                width=1,
                stipple="gray75",
            )

            label_y = zone.y_top + 2
            if (
                last_label_y is not None
                and abs(label_y - last_label_y) < _ZONE_LABEL_MIN_VERTICAL_GAP
            ):
                continue
            if zone.y_bottom - zone.y_top < _ZONE_LABEL_MIN_HEIGHT:
                continue
            if zone.label is None:
                continue

            self._canvas.create_text(
                zone.x_end - 4,
                label_y,
                text=zone.label,
                fill=outline,
                anchor="ne",
            )
            last_label_y = label_y

    def _draw_fibonacci_overlays(
        self,
        fibonacci_lines: tuple[FibonacciLinePrimitive, ...],
    ) -> None:
        for fibonacci_line in fibonacci_lines:
            self._canvas.create_line(
                fibonacci_line.x_start,
                fibonacci_line.y,
                fibonacci_line.x_end,
                fibonacci_line.y,
                fill="#ffb454",
                width=1,
                dash=(4, 3),
            )
            self._canvas.create_text(
                fibonacci_line.x_end - 4,
                fibonacci_line.y - 2,
                text=fibonacci_line.label,
                fill="#ffd79a",
                anchor="se",
            )

    def _draw_candlestick_pattern_overlays(
        self,
        patterns: tuple[CandlestickPatternPrimitive, ...],
    ) -> None:
        for pattern in patterns:
            self._canvas.create_text(
                pattern.x,
                pattern.y,
                text=pattern.label,
                fill=pattern.color,
                anchor="s",
            )

    def _draw_candlestick_pattern_status_hint(
        self,
        patterns: tuple[ChartCandlestickPattern, ...],
    ) -> None:
        if not self._show_candlestick_patterns_enabled() or not patterns:
            return

        statuses = {pattern.confirmation_status for pattern in patterns}
        if statuses == {"unknown"}:
            text = (
                "Kerzenformationen: geometrische Erkennung - "
                "zeitliche Bestaetigung nicht verfuegbar."
            )
        elif statuses == {"pending"}:
            text = "Kerzenformationen: geometrische Erkennung - zeitliche Bestaetigung ausstehend."
        elif statuses == {"confirmed"}:
            text = "Kerzenformationen: geometrische Erkennung - zeitlich bestaetigt."
        else:
            text = "Kerzenformationen: geometrische Erkennung - zeitlicher Status gemischt."

        self._canvas.create_text(
            _MARGIN_LEFT,
            _MARGIN_TOP,
            text=text,
            fill="#c5cedd",
            anchor="nw",
        )

    def _draw_axis_and_scenario_labels(
        self,
        time_labels: tuple[AxisLabel, ...],
        price_labels: tuple[AxisLabel, ...],
        scenario_labels: tuple[AxisLabel, ...],
    ) -> None:
        for time_label in time_labels:
            self._canvas.create_text(
                time_label.x,
                time_label.y,
                text=time_label.text,
                fill="#c5cedd",
                anchor="n",
            )
        for price_label in price_labels:
            self._canvas.create_text(
                price_label.x,
                price_label.y,
                text=price_label.text,
                fill="#c5cedd",
                anchor="e",
            )
        for scenario_label in scenario_labels:
            self._canvas.create_text(
                scenario_label.x,
                scenario_label.y,
                text=scenario_label.text,
                fill="#d7deea",
                anchor="nw",
            )

    def _draw_axes(self, *, width: int, height: int) -> None:
        plot_left = _MARGIN_LEFT
        plot_top = _MARGIN_TOP
        plot_right = width - _MARGIN_RIGHT
        plot_bottom = height - _MARGIN_BOTTOM
        self._canvas.create_line(plot_left, plot_top, plot_left, plot_bottom, fill="#6b778d")
        self._canvas.create_line(plot_left, plot_bottom, plot_right, plot_bottom, fill="#6b778d")

    def _on_canvas_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self._render()

    def _on_mouse_wheel(self, event: tk.Event[tk.Misc]) -> None:
        if event.delta > 0:
            self.zoom_in()
            return
        self.zoom_out()

    def _show_support_resistance_enabled(self) -> bool:
        var = getattr(self, "_show_support_resistance_var", None)
        if var is None:
            return True
        return bool(var.get())

    def _show_candlestick_patterns_enabled(self) -> bool:
        var = getattr(self, "_show_candlestick_patterns_var", None)
        if var is None:
            return True
        return bool(var.get())


def build_chart_render_model(
    *,
    candles: tuple[ChartCandle, ...],
    width: int,
    height: int,
    viewport: ChartViewport,
    swings: tuple[ChartSwing, ...] = (),
    pivots: tuple[ChartPivot, ...] = (),
    selected_waves: tuple[ChartWave, ...] = (),
    support_resistance_zones: tuple[ChartSupportResistanceZone, ...] = (),
    candlestick_patterns: tuple[ChartCandlestickPattern, ...] = (),
    forecast_scenarios: tuple[ChartForecastScenario, ...] = (),
    fibonacci_projections: tuple[ChartFibonacciProjection, ...] = (),
    max_visible_support_zones: int = _DEFAULT_VISIBLE_SUPPORT_ZONES,
    max_visible_resistance_zones: int = _DEFAULT_VISIBLE_RESISTANCE_ZONES,
    show_support_resistance_labels: bool = _SHOW_ZONE_LABELS_DEFAULT,
) -> ChartRenderModel:
    """Create a deterministic render model for the provided viewport."""

    if width <= _MARGIN_LEFT + _MARGIN_RIGHT or height <= _MARGIN_TOP + _MARGIN_BOTTOM:
        message = "canvas dimensions are too small for chart rendering"
        raise ValueError(message)

    ordered = tuple(sorted(candles, key=lambda candle: candle.opened_at))
    effective_viewport = viewport
    if viewport.total_candles != len(ordered):
        effective_viewport = ChartViewport.initial(len(ordered), viewport.visible_count)

    start = effective_viewport.start_index
    end = min(start + effective_viewport.visible_count, len(ordered))
    visible = ordered[start:end]
    if not visible:
        message = "viewport does not select any candles"
        raise ValueError(message)

    highs = tuple(candle.high_price for candle in visible)
    lows = tuple(candle.low_price for candle in visible)
    max_price = max(highs)
    min_price = min(lows)

    if max_price == min_price:
        max_price = max_price + Decimal("1")

    plot_left = _MARGIN_LEFT
    plot_top = _MARGIN_TOP
    plot_right = width - _MARGIN_RIGHT
    plot_bottom = height - _MARGIN_BOTTOM
    plot_width = plot_right - plot_left
    plot_height = plot_bottom - plot_top

    step = plot_width / len(visible)
    body_width = max(step * 0.62, 2.0)

    def map_price(price: Decimal) -> float:
        ratio = float((price - min_price) / (max_price - min_price))
        return plot_bottom - (ratio * plot_height)

    primitives, timestamp_x = _build_candle_primitives(
        visible=visible,
        plot_left=plot_left,
        step=step,
        body_width=body_width,
        map_price=map_price,
    )

    swing_lines, swing_markers, pivot_markers = _build_overlay_primitives(
        swings=swings,
        pivots=pivots,
        timestamp_x=timestamp_x,
        map_price=map_price,
    )
    wave_lines, wave_labels = _build_wave_primitives(
        selected_waves=selected_waves,
        timestamp_x=timestamp_x,
        map_price=map_price,
    )
    support_resistance_zone_primitives = _build_support_resistance_primitives(
        support_resistance_zones=_select_visible_support_resistance_zones(
            support_resistance_zones=support_resistance_zones,
            candles=visible,
            max_visible_support_zones=max_visible_support_zones,
            max_visible_resistance_zones=max_visible_resistance_zones,
        ),
        map_price=map_price,
        min_price=min_price,
        max_price=max_price,
        plot_top=plot_top,
        plot_bottom=plot_bottom,
        plot_left=plot_left,
        plot_right=plot_right,
        show_labels=show_support_resistance_labels,
    )
    candlestick_pattern_primitives = _build_candlestick_pattern_primitives(
        candlestick_patterns=candlestick_patterns,
        timestamp_x=timestamp_x,
        map_price=map_price,
    )
    fibonacci_lines = _build_fibonacci_lines(
        fibonacci_projections=fibonacci_projections,
        map_price=map_price,
        plot_top=plot_top,
        plot_bottom=plot_bottom,
        plot_left=plot_left,
        plot_right=plot_right,
    )
    scenario_labels = _build_scenario_labels(
        forecast_scenarios=forecast_scenarios,
        plot_left=plot_left,
        plot_top=plot_top,
    )

    time_labels = _build_time_axis_labels(
        visible=visible, plot_left=plot_left, plot_bottom=plot_bottom, step=step
    )
    price_labels = _build_price_axis_labels(
        min_price=min_price,
        max_price=max_price,
        plot_left=plot_left,
        plot_top=plot_top,
        plot_bottom=plot_bottom,
    )

    return ChartRenderModel(
        candles=visible,
        primitives=primitives,
        swing_lines=swing_lines,
        swing_markers=swing_markers,
        pivot_markers=pivot_markers,
        support_resistance_zones=support_resistance_zone_primitives,
        candlestick_patterns=candlestick_pattern_primitives,
        wave_lines=wave_lines,
        wave_labels=wave_labels,
        fibonacci_lines=fibonacci_lines,
        scenario_labels=scenario_labels,
        time_labels=time_labels,
        price_labels=price_labels,
        min_price=min_price,
        max_price=max_price,
    )


def _build_candle_primitives(
    *,
    visible: tuple[ChartCandle, ...],
    plot_left: float,
    step: float,
    body_width: float,
    map_price: Callable[[Decimal], float],
) -> tuple[tuple[CandlestickPrimitive, ...], dict[datetime, float]]:
    primitives: list[CandlestickPrimitive] = []
    timestamp_x: dict[datetime, float] = {}

    for index, candle in enumerate(visible):
        x_center = plot_left + (index + 0.5) * step
        timestamp_x[candle.opened_at] = x_center
        wick_top = map_price(candle.high_price)
        wick_bottom = map_price(candle.low_price)
        open_y = map_price(candle.open_price)
        close_y = map_price(candle.close_price)
        body_top = min(open_y, close_y)
        body_bottom = max(open_y, close_y)
        if body_bottom - body_top < 1.0:
            body_bottom = body_top + 1.0

        primitives.append(
            CandlestickPrimitive(
                opened_at=candle.opened_at,
                x_center=x_center,
                wick_top=wick_top,
                wick_bottom=wick_bottom,
                body_top=body_top,
                body_bottom=body_bottom,
                body_left=x_center - body_width / 2,
                body_right=x_center + body_width / 2,
                bullish=candle.close_price >= candle.open_price,
            )
        )

    return tuple(primitives), timestamp_x


def _build_overlay_primitives(
    *,
    swings: tuple[ChartSwing, ...],
    pivots: tuple[ChartPivot, ...],
    timestamp_x: dict[datetime, float],
    map_price: Callable[[Decimal], float],
) -> tuple[
    tuple[SwingLinePrimitive, ...],
    tuple[SwingMarkerPrimitive, ...],
    tuple[PivotMarkerPrimitive, ...],
]:
    confirmed_pivot_ids = {
        pivot_id for swing in swings for pivot_id in (swing.start_pivot_id, swing.end_pivot_id)
    }

    visible_pivots = tuple(
        sorted(
            (pivot for pivot in pivots if pivot.timestamp in timestamp_x),
            key=lambda pivot: (pivot.timestamp, pivot.pivot_id),
        )
    )

    pivot_markers = tuple(
        PivotMarkerPrimitive(
            pivot_id=pivot.pivot_id,
            timestamp=pivot.timestamp,
            pivot_type=pivot.pivot_type,
            x=timestamp_x[pivot.timestamp],
            y=map_price(pivot.price),
            confirmed=pivot.pivot_id in confirmed_pivot_ids,
        )
        for pivot in visible_pivots
    )

    confirmed_points = tuple(
        marker
        for marker in pivot_markers
        if marker.confirmed and marker.pivot_type in {"high", "low"}
    )
    swing_markers = tuple(
        SwingMarkerPrimitive(
            pivot_id=marker.pivot_id,
            timestamp=marker.timestamp,
            marker_type=marker.pivot_type,
            x=marker.x,
            y=marker.y,
        )
        for marker in confirmed_points
    )

    swing_lines: list[SwingLinePrimitive] = []
    for start_marker, end_marker in pairwise(swing_markers):
        swing_lines.append(
            SwingLinePrimitive(
                start_pivot_id=start_marker.pivot_id,
                end_pivot_id=end_marker.pivot_id,
                start_timestamp=start_marker.timestamp,
                end_timestamp=end_marker.timestamp,
                x1=start_marker.x,
                y1=start_marker.y,
                x2=end_marker.x,
                y2=end_marker.y,
                direction="up" if end_marker.y < start_marker.y else "down",
            )
        )

    return tuple(swing_lines), swing_markers, pivot_markers


def _build_wave_primitives(
    *,
    selected_waves: tuple[ChartWave, ...],
    timestamp_x: dict[datetime, float],
    map_price: Callable[[Decimal], float],
) -> tuple[tuple[WaveLinePrimitive, ...], tuple[WaveLabelPrimitive, ...]]:
    wave_lines: list[WaveLinePrimitive] = []
    wave_labels: list[WaveLabelPrimitive] = []

    for wave in sorted(selected_waves, key=lambda item: item.selection_rank):
        visible_anchors = [anchor for anchor in wave.anchors if anchor.timestamp in timestamp_x]
        if len(visible_anchors) < _MIN_WAVE_ANCHORS:
            continue

        degree_anchor = visible_anchors[0]
        wave_labels.append(
            WaveLabelPrimitive(
                wave_id=wave.wave_id,
                selection_rank=wave.selection_rank,
                x=timestamp_x[degree_anchor.timestamp],
                y=map_price(degree_anchor.price) - 10,
                text=f"{wave.wave_degree.upper()}#{wave.selection_rank}",
            )
        )

        for start_anchor, end_anchor in pairwise(visible_anchors):
            wave_lines.append(
                WaveLinePrimitive(
                    wave_id=wave.wave_id,
                    selection_rank=wave.selection_rank,
                    x1=timestamp_x[start_anchor.timestamp],
                    y1=map_price(start_anchor.price),
                    x2=timestamp_x[end_anchor.timestamp],
                    y2=map_price(end_anchor.price),
                )
            )

        for anchor in visible_anchors:
            if anchor.label is None:
                continue
            wave_labels.append(
                WaveLabelPrimitive(
                    wave_id=wave.wave_id,
                    selection_rank=wave.selection_rank,
                    x=timestamp_x[anchor.timestamp],
                    y=map_price(anchor.price) - 6,
                    text=anchor.label,
                )
            )

    return tuple(wave_lines), tuple(wave_labels)


def _build_support_resistance_primitives(
    *,
    support_resistance_zones: tuple[ChartSupportResistanceZone, ...],
    map_price: Callable[[Decimal], float],
    min_price: Decimal,
    max_price: Decimal,
    plot_top: float,
    plot_bottom: float,
    plot_left: float,
    plot_right: float,
    show_labels: bool,
) -> tuple[SupportResistanceZonePrimitive, ...]:
    primitives: list[SupportResistanceZonePrimitive] = []

    for zone in support_resistance_zones:
        if zone.upper_price < min_price or zone.lower_price > max_price:
            continue

        y_top = map_price(min(zone.upper_price, max_price))
        y_bottom = map_price(max(zone.lower_price, min_price))
        y_top = max(y_top, plot_top)
        y_bottom = min(y_bottom, plot_bottom)
        if y_bottom - y_top < 1.0:
            y_bottom = y_top + 1.0

        label_prefix = "SUP" if zone.zone_type == "support" else "RES"
        primitives.append(
            SupportResistanceZonePrimitive(
                zone_type=zone.zone_type,
                y_top=y_top,
                y_bottom=y_bottom,
                x_start=plot_left,
                x_end=plot_right,
                touch_count=zone.touch_count,
                label=f"{label_prefix} x{zone.touch_count}" if show_labels else None,
            )
        )

    return _filter_visually_distinct_primitives(tuple(primitives))


def _select_visible_support_resistance_zones(
    *,
    support_resistance_zones: tuple[ChartSupportResistanceZone, ...],
    candles: tuple[ChartCandle, ...],
    max_visible_support_zones: int,
    max_visible_resistance_zones: int,
) -> tuple[ChartSupportResistanceZone, ...]:
    if not support_resistance_zones or not candles:
        return ()

    as_of_timestamp = candles[-1].opened_at
    reference_price = candles[-1].close_price
    available = tuple(
        zone for zone in support_resistance_zones if zone.last_timestamp <= as_of_timestamp
    )

    supports = _top_relevant_zones(
        zones=tuple(zone for zone in available if zone.zone_type == "support"),
        as_of_timestamp=as_of_timestamp,
        reference_price=reference_price,
        limit=_resolve_zone_limit(max_visible_support_zones),
    )
    resistances = _top_relevant_zones(
        zones=tuple(zone for zone in available if zone.zone_type == "resistance"),
        as_of_timestamp=as_of_timestamp,
        reference_price=reference_price,
        limit=_resolve_zone_limit(max_visible_resistance_zones),
    )
    return supports + resistances


def _top_relevant_zones(
    *,
    zones: tuple[ChartSupportResistanceZone, ...],
    as_of_timestamp: datetime,
    reference_price: Decimal,
    limit: int,
) -> tuple[ChartSupportResistanceZone, ...]:
    scored: list[_ZoneRelevanceScore] = []
    for zone in zones:
        midpoint = (zone.lower_price + zone.upper_price) / Decimal("2")
        distance = abs(reference_price - midpoint)
        recency = as_of_timestamp - zone.last_timestamp
        if recency < timedelta(0):
            continue

        touch_score = zone.touch_count * 100
        recency_score = 1000.0 / (1.0 + recency.total_seconds())
        proximity_score = 1000.0 / (1.0 + float(distance))
        scored.append(
            _ZoneRelevanceScore(
                zone=zone,
                touch_score=touch_score,
                recency_score=recency_score,
                proximity_score=proximity_score,
            )
        )

    selected = sorted(
        scored,
        key=lambda item: (
            -item.total_score,
            -item.zone.touch_count,
            -item.zone.last_timestamp.timestamp(),
            abs(
                float(
                    ((item.zone.lower_price + item.zone.upper_price) / Decimal("2"))
                    - reference_price
                )
            ),
            item.zone.lower_price,
            item.zone.upper_price,
        ),
    )[:limit]

    return tuple(item.zone for item in selected)


def _resolve_zone_limit(requested_limit: int) -> int:
    return min(max(0, requested_limit), _MAX_VISIBLE_ZONE_LIMIT)


def _filter_visually_distinct_primitives(
    primitives: tuple[SupportResistanceZonePrimitive, ...],
) -> tuple[SupportResistanceZonePrimitive, ...]:
    accepted: list[SupportResistanceZonePrimitive] = []

    for primitive in primitives:
        same_type = [item for item in accepted if item.zone_type == primitive.zone_type]
        if any(_is_visually_similar(primitive, item) for item in same_type):
            continue
        accepted.append(primitive)

    return tuple(
        sorted(
            accepted,
            key=lambda primitive: (
                primitive.zone_type,
                primitive.y_top,
                primitive.y_bottom,
            ),
        )
    )


def _is_visually_similar(
    left: SupportResistanceZonePrimitive,
    right: SupportResistanceZonePrimitive,
) -> bool:
    left_height = max(left.y_bottom - left.y_top, 1.0)
    right_height = max(right.y_bottom - right.y_top, 1.0)

    overlap = max(0.0, min(left.y_bottom, right.y_bottom) - max(left.y_top, right.y_top))
    overlap_ratio = overlap / min(left_height, right_height)
    if overlap_ratio >= _ZONE_STRONG_OVERLAP_RATIO:
        return True

    left_center = (left.y_top + left.y_bottom) / 2
    right_center = (right.y_top + right.y_bottom) / 2
    return abs(left_center - right_center) < _ZONE_VISUAL_MIN_GAP_PIXELS


def _build_candlestick_pattern_primitives(
    *,
    candlestick_patterns: tuple[ChartCandlestickPattern, ...],
    timestamp_x: dict[datetime, float],
    map_price: Callable[[Decimal], float],
) -> tuple[CandlestickPatternPrimitive, ...]:
    if not candlestick_patterns:
        return ()

    groups: dict[datetime, list[ChartCandlestickPattern]] = {}
    for pattern in candlestick_patterns:
        if pattern.ended_at not in timestamp_x:
            continue
        groups.setdefault(pattern.ended_at, []).append(pattern)

    selected_groups = sorted(
        groups.items(),
        key=lambda item: _pattern_group_sort_key(item[0], tuple(item[1])),
    )[:_DEFAULT_VISIBLE_PATTERN_MARKERS]

    primitives: list[CandlestickPatternPrimitive] = []
    last_x: float | None = None
    for ended_at, patterns in selected_groups:
        ordered_patterns = sorted(patterns, key=_pattern_priority_key)
        labels = [pattern.short_label for pattern in ordered_patterns]
        merged_label = labels[0] if len(labels) == 1 else f"{labels[0]}+{len(labels) - 1}"

        primary = ordered_patterns[0]
        x = timestamp_x[ended_at]
        y = map_price(primary.price_anchor)
        if primary.direction == "bullish":
            y += 12
            color = "#7bd88f"
        elif primary.direction == "bearish":
            y -= 12
            color = "#ff7f7f"
        else:
            y -= 10
            color = "#a8a8a8"

        if last_x is not None and abs(x - last_x) < _PATTERN_LABEL_MIN_X_GAP:
            continue
        last_x = x

        primitives.append(
            CandlestickPatternPrimitive(
                ended_at=ended_at,
                x=x,
                y=y,
                label=merged_label,
                color=color,
            )
        )

    return tuple(
        sorted(
            primitives,
            key=lambda pattern: (pattern.ended_at, pattern.label),
        )
    )


def _pattern_group_sort_key(
    ended_at: datetime,
    patterns: tuple[ChartCandlestickPattern, ...],
) -> tuple[int, float, datetime]:
    multi_candle_score = max(len(pattern.candle_timestamps) for pattern in patterns)
    geometric_score = max(float(pattern.geometric_score) for pattern in patterns)
    return (-multi_candle_score, -geometric_score, ended_at)


def _pattern_priority_key(pattern: ChartCandlestickPattern) -> tuple[int, float, str]:
    return (
        -len(pattern.candle_timestamps),
        -float(pattern.geometric_score),
        pattern.pattern_type,
    )


def _build_fibonacci_lines(
    *,
    fibonacci_projections: tuple[ChartFibonacciProjection, ...],
    map_price: Callable[[Decimal], float],
    plot_top: float,
    plot_bottom: float,
    plot_left: float,
    plot_right: float,
) -> tuple[FibonacciLinePrimitive, ...]:
    lines: list[FibonacciLinePrimitive] = []

    for projection in fibonacci_projections:
        y = map_price(projection.price)
        if y < plot_top or y > plot_bottom:
            continue

        lines.append(
            FibonacciLinePrimitive(
                ratio=projection.level_ratio,
                price=projection.price,
                y=y,
                x_start=plot_left,
                x_end=plot_right,
                label=f"FIB {projection.level_ratio:.3f} @ {projection.price:.2f}",
            )
        )

    return tuple(lines)


def _build_scenario_labels(
    *,
    forecast_scenarios: tuple[ChartForecastScenario, ...],
    plot_left: float,
    plot_top: float,
) -> tuple[AxisLabel, ...]:
    labels: list[AxisLabel] = []
    y = plot_top + 6
    for scenario in forecast_scenarios:
        scenario_prefix = {
            "primary": "PRIMARY",
            "alternative": "ALT",
            "invalidated": "INVALID",
        }.get(scenario.scenario_type, scenario.scenario_type.upper())
        labels.append(
            AxisLabel(
                x=plot_left + 8,
                y=y,
                text=(
                    f"{scenario_prefix}: {scenario.expected_next_wave} ({scenario.confidence:.1f}%)"
                ),
            )
        )
        y += 14

    return tuple(labels)


def _build_time_axis_labels(
    *,
    visible: tuple[ChartCandle, ...],
    plot_left: float,
    plot_bottom: float,
    step: float,
) -> tuple[AxisLabel, ...]:
    target_count = min(6, len(visible))

    labels: list[AxisLabel] = []
    for label_index in range(target_count):
        source_index = round((len(visible) - 1) * (label_index / max(target_count - 1, 1)))
        candle = visible[source_index]
        x = plot_left + (source_index + 0.5) * step
        labels.append(
            AxisLabel(
                x=x,
                y=plot_bottom + 6,
                text=candle.opened_at.strftime("%m-%d %H:%M"),
            )
        )

    return tuple(labels)


def _build_price_axis_labels(
    *,
    min_price: Decimal,
    max_price: Decimal,
    plot_left: float,
    plot_top: float,
    plot_bottom: float,
) -> tuple[AxisLabel, ...]:
    label_count = 5
    labels: list[AxisLabel] = []
    for label_index in range(label_count):
        ratio = label_index / (label_count - 1)
        y = plot_bottom - ((plot_bottom - plot_top) * ratio)
        value = min_price + ((max_price - min_price) * Decimal(str(ratio)))
        labels.append(
            AxisLabel(
                x=plot_left - 6,
                y=y,
                text=f"{value:.2f}",
            )
        )
    return tuple(labels)


def _clamp_visible(visible_count: int, total_candles: int) -> int:
    if total_candles <= 0:
        return _MIN_VISIBLE_CANDLES

    return min(max(visible_count, _MIN_VISIBLE_CANDLES), total_candles)


def _ensure_main_thread() -> None:
    if threading.current_thread() is not threading.main_thread():
        message = "chart UI operations must run on the Tk main thread"
        raise RuntimeError(message)
