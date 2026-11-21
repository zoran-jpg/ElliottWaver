from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from elliottwaver.application.chart_contract import (
    ChartCandle,
    ChartDataContract,
    ChartFibonacciProjection,
    ChartForecastScenario,
    ChartPivot,
    ChartProjectionTarget,
    ChartSwing,
    ChartWave,
    ChartWaveAnchor,
    TimeframeChartData,
)
from elliottwaver.interfaces.chart_tk import (
    CandlestickChartView,
    ChartViewport,
    _ensure_main_thread,
    build_chart_render_model,
)


def _candles() -> tuple[ChartCandle, ...]:
    return (
        ChartCandle(
            opened_at=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            open_price=Decimal("105"),
            high_price=Decimal("108"),
            low_price=Decimal("104"),
            close_price=Decimal("107"),
        ),
        ChartCandle(
            opened_at=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            open_price=Decimal("100"),
            high_price=Decimal("103"),
            low_price=Decimal("99"),
            close_price=Decimal("102"),
        ),
        ChartCandle(
            opened_at=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
            open_price=Decimal("102"),
            high_price=Decimal("104"),
            low_price=Decimal("101"),
            close_price=Decimal("101"),
        ),
    )


def _contract() -> ChartDataContract:
    return ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )


@dataclass(slots=True)
class _FakeCanvas:
    deleted: list[str]
    texts: list[tuple[float, float, str]]
    lines: list[tuple[float, float, float, float]]
    rectangles: list[tuple[float, float, float, float]]
    ovals: list[tuple[float, float, float, float]]
    polygons: list[tuple[float, ...]]
    width: int = 900
    height: int = 420

    def __init__(self, width: int = 900, height: int = 420) -> None:
        self.deleted = []
        self.texts = []
        self.lines = []
        self.rectangles = []
        self.ovals = []
        self.polygons = []
        self.width = width
        self.height = height

    def delete(self, target: str) -> None:
        self.deleted.append(target)

    def create_text(
        self,
        x: float,
        y: float,
        *,
        text: str,
        fill: str,
        anchor: str,
    ) -> None:
        _ = fill, anchor
        self.texts.append((x, y, text))

    def create_line(self, x1: float, y1: float, x2: float, y2: float, **_kwargs: object) -> None:
        self.lines.append((x1, y1, x2, y2))

    def create_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        **_kwargs: object,
    ) -> None:
        self.rectangles.append((x1, y1, x2, y2))

    def create_oval(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        **_kwargs: object,
    ) -> None:
        self.ovals.append((x1, y1, x2, y2))

    def create_polygon(self, *points: float, **_kwargs: object) -> None:
        self.polygons.append(tuple(points))

    def winfo_width(self) -> int:
        return self.width

    def winfo_height(self) -> int:
        return self.height


@dataclass(frozen=True, slots=True)
class _MouseEvent:
    delta: int


def _view_stub(*, with_contract: bool) -> Any:
    view: Any = object.__new__(CandlestickChartView)
    view._canvas = _FakeCanvas()
    view._timeframe_index = 0
    view._contract = _contract() if with_contract else None
    view._viewport = ChartViewport.initial(3, visible_count=3)
    return view


def _overlay_primitives() -> tuple[tuple[ChartPivot, ...], tuple[ChartSwing, ...]]:
    pivots = (
        ChartPivot(
            pivot_id="p1",
            timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            price=Decimal("99"),
            pivot_type="low",
        ),
        ChartPivot(
            pivot_id="p2",
            timestamp=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
            price=Decimal("104"),
            pivot_type="high",
        ),
        ChartPivot(
            pivot_id="p3",
            timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            price=Decimal("101"),
            pivot_type="low",
        ),
        ChartPivot(
            pivot_id="p4",
            timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            price=Decimal("103"),
            pivot_type="high",
        ),
    )
    swings = (
        ChartSwing(
            swing_id="s1",
            direction="up",
            start_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            end_timestamp=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
            start_price=Decimal("99"),
            end_price=Decimal("104"),
            start_pivot_id="p1",
            end_pivot_id="p2",
        ),
        ChartSwing(
            swing_id="s2",
            direction="down",
            start_timestamp=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
            end_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            start_price=Decimal("104"),
            end_price=Decimal("101"),
            start_pivot_id="p2",
            end_pivot_id="p3",
        ),
    )
    return pivots, swings


def test_build_chart_render_model_maps_ohlc_and_keeps_chronological_order() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)

    model = build_chart_render_model(candles=candles, width=900, height=400, viewport=viewport)

    assert [candle.opened_at for candle in model.candles] == [
        datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
        datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
    ]
    assert len(model.primitives) == 3
    assert model.primitives[0].opened_at == datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    assert model.primitives[0].bullish is True
    assert model.primitives[1].bullish is False
    assert model.primitives[0].wick_top <= model.primitives[0].body_top
    assert model.primitives[0].wick_bottom >= model.primitives[0].body_bottom


def test_build_chart_render_model_creates_time_and_price_axes_labels() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)

    model = build_chart_render_model(candles=candles, width=900, height=400, viewport=viewport)

    assert len(model.time_labels) >= 1
    assert len(model.price_labels) == 5
    assert all(label.text for label in model.time_labels)
    assert all(label.text for label in model.price_labels)


def test_build_chart_render_model_maps_pivots_and_confirmed_swings() -> None:
    candles = _candles()
    pivots, swings = _overlay_primitives()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        swings=swings,
        pivots=pivots,
    )

    assert len(model.pivot_markers) == 4
    assert [marker.pivot_id for marker in model.swing_markers] == ["p1", "p2", "p3"]
    assert [marker.marker_type for marker in model.swing_markers] == ["low", "high", "low"]
    assert [line.start_pivot_id for line in model.swing_lines] == ["p1", "p2"]
    assert [line.end_pivot_id for line in model.swing_lines] == ["p2", "p3"]
    assert model.swing_lines[0].direction == "up"
    assert model.swing_lines[1].direction == "down"


def test_build_chart_render_model_prevents_look_ahead_from_unconfirmed_pivots() -> None:
    candles = _candles()
    pivots, swings = _overlay_primitives()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        swings=swings,
        pivots=pivots,
    )

    unconfirmed = next(marker for marker in model.pivot_markers if marker.pivot_id == "p4")
    assert unconfirmed.confirmed is False
    assert all(marker.pivot_id != "p4" for marker in model.swing_markers)


def test_build_chart_render_model_aligns_overlay_coordinates_with_candles() -> None:
    candles = _candles()
    pivots, swings = _overlay_primitives()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        swings=swings,
        pivots=pivots,
    )

    candle_x = {primitive.opened_at: primitive.x_center for primitive in model.primitives}
    marker_p2 = next(marker for marker in model.swing_markers if marker.pivot_id == "p2")
    assert marker_p2.x == candle_x[datetime(2026, 7, 21, 1, 0, tzinfo=UTC)]


def test_build_chart_render_model_clips_overlay_to_viewport_window() -> None:
    candles = _candles()
    pivots, swings = _overlay_primitives()
    viewport = ChartViewport(start_index=1, visible_count=2, total_candles=3)

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        swings=swings,
        pivots=pivots,
    )

    assert [candle.opened_at for candle in model.candles] == [
        datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
        datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
    ]
    assert [marker.pivot_id for marker in model.swing_markers] == ["p2", "p3"]
    assert len(model.swing_lines) == 1
    assert model.swing_lines[0].start_pivot_id == "p2"
    assert model.swing_lines[0].end_pivot_id == "p3"


def test_build_chart_render_model_handles_empty_or_incomplete_overlay_data() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        swings=(),
        pivots=(),
    )

    assert model.pivot_markers == ()
    assert model.swing_markers == ()
    assert model.swing_lines == ()


def test_overlay_primitives_follow_zoom_pan_and_reset_viewport() -> None:
    base = datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    candles = tuple(
        ChartCandle(
            opened_at=base + timedelta(hours=index),
            open_price=Decimal(100 + index),
            high_price=Decimal(103 + index),
            low_price=Decimal(99 + index),
            close_price=Decimal(101 + index),
        )
        for index in range(20)
    )
    pivots = (
        ChartPivot(
            pivot_id="p1",
            timestamp=base + timedelta(hours=7),
            price=Decimal("102"),
            pivot_type="low",
        ),
        ChartPivot(
            pivot_id="p2",
            timestamp=base + timedelta(hours=9),
            price=Decimal("106"),
            pivot_type="high",
        ),
        ChartPivot(
            pivot_id="p3",
            timestamp=base + timedelta(hours=12),
            price=Decimal("104"),
            pivot_type="low",
        ),
        ChartPivot(
            pivot_id="p4",
            timestamp=base + timedelta(hours=15),
            price=Decimal("110"),
            pivot_type="high",
        ),
    )
    swings = (
        ChartSwing(
            swing_id="s1",
            direction="up",
            start_timestamp=base + timedelta(hours=7),
            end_timestamp=base + timedelta(hours=9),
            start_price=Decimal("102"),
            end_price=Decimal("106"),
            start_pivot_id="p1",
            end_pivot_id="p2",
        ),
        ChartSwing(
            swing_id="s2",
            direction="down",
            start_timestamp=base + timedelta(hours=9),
            end_timestamp=base + timedelta(hours=12),
            start_price=Decimal("106"),
            end_price=Decimal("104"),
            start_pivot_id="p2",
            end_pivot_id="p3",
        ),
        ChartSwing(
            swing_id="s3",
            direction="up",
            start_timestamp=base + timedelta(hours=12),
            end_timestamp=base + timedelta(hours=15),
            start_price=Decimal("104"),
            end_price=Decimal("110"),
            start_pivot_id="p3",
            end_pivot_id="p4",
        ),
    )

    initial = ChartViewport.initial(total_candles=len(candles), visible_count=12)
    zoomed = initial.zoom(-2)
    panned = zoomed.pan(-2)
    reset = ChartViewport.initial(total_candles=len(candles), visible_count=12)

    initial_model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=initial,
        swings=swings,
        pivots=pivots,
    )
    zoomed_model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=zoomed,
        swings=swings,
        pivots=pivots,
    )
    panned_model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=panned,
        swings=swings,
        pivots=pivots,
    )
    reset_model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=reset,
        swings=swings,
        pivots=pivots,
    )

    assert [marker.pivot_id for marker in initial_model.swing_markers] == ["p2", "p3", "p4"]
    assert [marker.pivot_id for marker in zoomed_model.swing_markers] == ["p3", "p4"]
    assert [marker.pivot_id for marker in panned_model.swing_markers] == ["p2", "p3", "p4"]
    assert [marker.pivot_id for marker in reset_model.swing_markers] == ["p2", "p3", "p4"]


def test_build_chart_render_model_maps_wave_overlays_without_anchor_substitution() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    missing_timestamp = datetime(2026, 7, 21, 3, 0, tzinfo=UTC)
    selected_waves = (
        ChartWave(
            wave_id="wave-1",
            wave_type="impulse",
            wave_degree="primary",
            selection_rank=1,
            anchors=(
                ChartWaveAnchor(
                    pivot_id="p1",
                    timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                    price=Decimal("99"),
                    label=None,
                ),
                ChartWaveAnchor(
                    pivot_id="p2",
                    timestamp=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                    price=Decimal("104"),
                    label="1",
                ),
                ChartWaveAnchor(
                    pivot_id="p3",
                    timestamp=missing_timestamp,
                    price=Decimal("102"),
                    label="2",
                ),
            ),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        selected_waves=selected_waves,
    )

    assert len(model.wave_lines) == 1
    assert [label.text for label in model.wave_labels] == ["PRIMARY#1", "1"]


def test_build_chart_render_model_maps_fibonacci_targets_in_visible_price_range() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    fibonacci = (
        ChartFibonacciProjection(
            level_ratio=Decimal("0.618"),
            price=Decimal("104"),
            direction="up",
            reference_range=Decimal("12"),
        ),
        ChartFibonacciProjection(
            level_ratio=Decimal("1.618"),
            price=Decimal("500"),
            direction="up",
            reference_range=Decimal("12"),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        fibonacci_projections=fibonacci,
    )

    assert len(model.fibonacci_lines) == 1
    assert model.fibonacci_lines[0].ratio == Decimal("0.618")
    assert "0.618" in model.fibonacci_lines[0].label
    assert "104.00" in model.fibonacci_lines[0].label


def test_build_chart_render_model_includes_primary_and_alternative_scenarios() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    scenarios = (
        ChartForecastScenario(
            scenario_type="primary",
            expected_next_wave="Wave 5",
            confidence=Decimal("72"),
            reasoning=("Momentum remains intact",),
            projection_targets=(
                ChartProjectionTarget(
                    priority=1,
                    target_price=Decimal("116"),
                    confidence=Decimal("72"),
                    wave_degree="primary",
                    description="Primary target",
                ),
            ),
        ),
        ChartForecastScenario(
            scenario_type="alternative",
            expected_next_wave="Wave C",
            confidence=Decimal("28"),
            reasoning=("Corrective pressure",),
            projection_targets=(
                ChartProjectionTarget(
                    priority=1,
                    target_price=Decimal("96"),
                    confidence=Decimal("28"),
                    wave_degree="secondary",
                    description="Alternative target",
                ),
            ),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        forecast_scenarios=scenarios,
    )

    assert [label.text for label in model.scenario_labels] == [
        "PRIMARY: Wave 5 (72.0%)",
        "ALT: Wave C (28.0%)",
    ]


def test_chart_viewport_supports_zoom_and_navigation() -> None:
    viewport = ChartViewport.initial(total_candles=120, visible_count=40)

    panned = viewport.pan(-10)
    zoomed_in = panned.zoom(-8)
    zoomed_out = zoomed_in.zoom(24)

    assert viewport.start_index == 80
    assert panned.start_index == 70
    assert zoomed_in.visible_count == 32
    assert zoomed_out.visible_count == 56
    assert 0 <= zoomed_out.start_index <= zoomed_out.total_candles - zoomed_out.visible_count


def test_chart_viewport_clamps_pan_and_zoom_bounds() -> None:
    viewport = ChartViewport.initial(total_candles=20, visible_count=20)

    assert viewport.start_index == 0
    assert viewport.pan(-500).start_index == 0
    assert viewport.pan(500).start_index == 0

    zoomed_in = viewport.zoom(-200)
    assert zoomed_in.visible_count == 8
    assert zoomed_in.start_index == 12

    zoomed_back = zoomed_in.zoom(999)
    assert zoomed_back.visible_count == 20
    assert zoomed_back.start_index == 0


def test_build_chart_render_model_rejects_empty_or_invalid_dimensions() -> None:
    viewport = ChartViewport.initial(total_candles=0)

    with pytest.raises(ValueError, match="too small"):
        build_chart_render_model(candles=_candles(), width=50, height=40, viewport=viewport)

    with pytest.raises(ValueError, match="does not select any candles"):
        build_chart_render_model(candles=(), width=900, height=400, viewport=viewport)


def test_build_chart_render_model_enforces_minimum_body_height_for_flat_body() -> None:
    candles = (
        ChartCandle(
            opened_at=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            open_price=Decimal("100"),
            high_price=Decimal("102"),
            low_price=Decimal("98"),
            close_price=Decimal("100"),
        ),
    )
    viewport = ChartViewport.initial(total_candles=1, visible_count=1)

    model = build_chart_render_model(candles=candles, width=600, height=240, viewport=viewport)

    primitive = model.primitives[0]
    assert primitive.body_bottom - primitive.body_top >= 1.0
    assert primitive.wick_top <= primitive.body_top
    assert primitive.wick_bottom >= primitive.body_bottom


def test_main_thread_guard_rejects_non_main_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SentinelThread:
        pass

    current = _SentinelThread()
    main = _SentinelThread()

    monkeypatch.setattr(
        "elliottwaver.interfaces.chart_tk.threading.current_thread", lambda: current
    )
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk.threading.main_thread", lambda: main)

    with pytest.raises(RuntimeError, match="main thread"):
        _ensure_main_thread()


def test_chart_view_render_contract_and_clear_manage_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)

    view = _view_stub(with_contract=False)
    render_calls: list[str] = []
    view._render = lambda: render_calls.append("render")

    contract = _contract()
    view.render_contract(contract)

    assert view._contract == contract
    assert view._viewport.total_candles == 3
    assert render_calls == ["render"]

    view.clear()
    assert view._contract is None
    assert view._viewport.total_candles == 0
    assert view._canvas.deleted[-1] == "all"


def test_chart_view_controls_adjust_viewport_and_request_rerender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)

    view = _view_stub(with_contract=True)
    render_calls: list[str] = []
    view._render = lambda: render_calls.append("render")

    original_visible = view._viewport.visible_count
    view.zoom_in()
    assert view._viewport.visible_count <= original_visible

    view.zoom_out()
    view.pan_left()
    view.pan_right()
    view.reset_view()

    assert len(render_calls) == 5


def test_chart_view_reset_restores_latest_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)

    view = _view_stub(with_contract=True)
    view._viewport = ChartViewport(start_index=0, visible_count=8, total_candles=3)
    view._render = lambda: None

    view.reset_view()

    assert view._viewport == ChartViewport.initial(total_candles=3)


def test_chart_view_render_draws_placeholder_when_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)
    view = _view_stub(with_contract=False)

    view._render()

    assert view._canvas.deleted == ["all"]
    assert any("Keine Chart-Daten" in text for _, _, text in view._canvas.texts)


def test_chart_view_render_draws_candles_and_axes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)
    view = _view_stub(with_contract=True)

    view._render()

    assert len(view._canvas.rectangles) == 3
    assert len(view._canvas.lines) >= 5


def test_chart_view_render_draws_overlay_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)
    view = _view_stub(with_contract=True)

    pivots, swings = _overlay_primitives()
    view._contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=swings,
                pivots=pivots,
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )

    view._render()

    assert len(view._canvas.ovals) == 4
    assert len(view._canvas.polygons) == 3


def test_chart_view_mouse_wheel_routes_to_zoom_actions() -> None:
    view = _view_stub(with_contract=True)
    calls: list[str] = []
    view.zoom_in = lambda: calls.append("in")
    view.zoom_out = lambda: calls.append("out")

    view._on_mouse_wheel(_MouseEvent(delta=120))
    view._on_mouse_wheel(_MouseEvent(delta=-120))

    assert calls == ["in", "out"]


def test_chart_view_canvas_configure_triggers_render() -> None:
    view = _view_stub(with_contract=True)
    calls: list[str] = []
    view._render = lambda: calls.append("render")

    view._on_canvas_configure(object())

    assert calls == ["render"]
