from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import combinations
from typing import Any

import pytest

from elliottwaver.application.chart_contract import (
    ChartCandle,
    ChartCandlestickPattern,
    ChartDataContract,
    ChartFibonacciProjection,
    ChartForecastScenario,
    ChartPivot,
    ChartProjectionTarget,
    ChartSupportResistanceZone,
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
    operations: list[str]
    width: int = 900
    height: int = 420

    def __init__(self, width: int = 900, height: int = 420) -> None:
        self.deleted = []
        self.texts = []
        self.lines = []
        self.rectangles = []
        self.ovals = []
        self.polygons = []
        self.operations = []
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
        self.operations.append("text")
        self.texts.append((x, y, text))

    def create_line(self, x1: float, y1: float, x2: float, y2: float, **_kwargs: object) -> None:
        self.operations.append("line")
        self.lines.append((x1, y1, x2, y2))

    def create_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        **_kwargs: object,
    ) -> None:
        if "stipple" in _kwargs:
            self.operations.append("zone-rectangle")
        else:
            self.operations.append("candle-rectangle")
        self.rectangles.append((x1, y1, x2, y2))

    def create_oval(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        **_kwargs: object,
    ) -> None:
        self.operations.append("oval")
        self.ovals.append((x1, y1, x2, y2))

    def create_polygon(self, *points: float, **_kwargs: object) -> None:
        self.operations.append("polygon")
        self.polygons.append(tuple(points))

    def winfo_width(self) -> int:
        return self.width

    def winfo_height(self) -> int:
        return self.height


@dataclass(frozen=True, slots=True)
class _MouseEvent:
    delta: int


@dataclass(frozen=True, slots=True)
class _FakeBoolVar:
    value: bool

    def get(self) -> bool:
        return self.value


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


def test_build_chart_render_model_maps_support_resistance_zones_in_visible_range() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    zones = (
        ChartSupportResistanceZone(
            zone_type="support",
            lower_price=Decimal("99"),
            upper_price=Decimal("101"),
            touch_count=2,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("p1", "p3"),
        ),
        ChartSupportResistanceZone(
            zone_type="resistance",
            lower_price=Decimal("500"),
            upper_price=Decimal("510"),
            touch_count=1,
            first_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("p2",),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        support_resistance_zones=zones,
    )

    assert len(model.support_resistance_zones) == 1
    assert model.support_resistance_zones[0].zone_type == "support"
    assert model.support_resistance_zones[0].touch_count == 2
    assert model.support_resistance_zones[0].label is None


def test_build_chart_render_model_limits_visible_zones_per_type_to_default_3() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    zones = tuple(
        ChartSupportResistanceZone(
            zone_type="support" if index < 7 else "resistance",
            lower_price=Decimal(str(95 + index)),
            upper_price=Decimal(str(96 + index)),
            touch_count=index + 1,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=(f"p{index}",),
        )
        for index in range(14)
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        support_resistance_zones=zones,
    )

    assert len(zones) == 14
    supports = [zone for zone in model.support_resistance_zones if zone.zone_type == "support"]
    resistances = [
        zone for zone in model.support_resistance_zones if zone.zone_type == "resistance"
    ]
    assert len(supports) <= 3
    assert len(resistances) <= 3


def test_build_chart_render_model_supports_configurable_limit_up_to_5_per_type() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    zones = tuple(
        ChartSupportResistanceZone(
            zone_type="support" if index < 8 else "resistance",
            lower_price=Decimal(str(95 + index)),
            upper_price=Decimal(str(96 + index)),
            touch_count=index + 1,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=(f"p{index}",),
        )
        for index in range(16)
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        support_resistance_zones=zones,
        max_visible_support_zones=5,
        max_visible_resistance_zones=5,
    )

    supports = [zone for zone in model.support_resistance_zones if zone.zone_type == "support"]
    resistances = [
        zone for zone in model.support_resistance_zones if zone.zone_type == "resistance"
    ]
    assert len(supports) <= 5
    assert len(resistances) <= 5


def test_build_chart_render_model_filters_visually_overlapping_zones() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    zones = (
        ChartSupportResistanceZone(
            zone_type="support",
            lower_price=Decimal("100.00"),
            upper_price=Decimal("101.00"),
            touch_count=5,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("s1",),
        ),
        ChartSupportResistanceZone(
            zone_type="support",
            lower_price=Decimal("100.10"),
            upper_price=Decimal("101.10"),
            touch_count=4,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("s2",),
        ),
        ChartSupportResistanceZone(
            zone_type="support",
            lower_price=Decimal("100.20"),
            upper_price=Decimal("101.20"),
            touch_count=3,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("s3",),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        support_resistance_zones=zones,
        max_visible_support_zones=3,
    )

    supports = [zone for zone in model.support_resistance_zones if zone.zone_type == "support"]
    assert len(supports) < 3


def test_build_chart_render_model_never_displays_strongly_overlapping_same_type_zones() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    zones = (
        ChartSupportResistanceZone(
            zone_type="resistance",
            lower_price=Decimal("106.00"),
            upper_price=Decimal("107.00"),
            touch_count=7,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("r1",),
        ),
        ChartSupportResistanceZone(
            zone_type="resistance",
            lower_price=Decimal("106.10"),
            upper_price=Decimal("107.10"),
            touch_count=6,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("r2",),
        ),
        ChartSupportResistanceZone(
            zone_type="resistance",
            lower_price=Decimal("107.80"),
            upper_price=Decimal("108.20"),
            touch_count=5,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("r3",),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        support_resistance_zones=zones,
        max_visible_resistance_zones=5,
    )

    resistances = [
        zone for zone in model.support_resistance_zones if zone.zone_type == "resistance"
    ]
    for left, right in combinations(resistances, 2):
        left_height = max(left.y_bottom - left.y_top, 1.0)
        right_height = max(right.y_bottom - right.y_top, 1.0)
        overlap = max(0.0, min(left.y_bottom, right.y_bottom) - max(left.y_top, right.y_top))
        overlap_ratio = overlap / min(left_height, right_height)
        assert overlap_ratio < 0.6


def test_build_chart_render_model_selects_zones_deterministically() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    zones = (
        ChartSupportResistanceZone(
            zone_type="support",
            lower_price=Decimal("99"),
            upper_price=Decimal("100"),
            touch_count=3,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("a",),
        ),
        ChartSupportResistanceZone(
            zone_type="support",
            lower_price=Decimal("98"),
            upper_price=Decimal("99"),
            touch_count=3,
            first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
            pivot_ids=("b",),
        ),
    )

    first = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        support_resistance_zones=zones,
    )
    second = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        support_resistance_zones=zones,
    )

    assert first.support_resistance_zones == second.support_resistance_zones


def test_build_chart_render_model_limits_and_sorts_candlestick_markers() -> None:
    base = datetime(2026, 7, 21, 0, 0, tzinfo=UTC)
    candles = tuple(
        ChartCandle(
            opened_at=base + timedelta(hours=index),
            open_price=Decimal("100"),
            high_price=Decimal("102"),
            low_price=Decimal("98"),
            close_price=Decimal("101"),
        )
        for index in range(20)
    )
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=20)
    patterns = tuple(
        ChartCandlestickPattern(
            pattern_id=f"p-{index}",
            pattern_type="bullish_engulfing",
            short_label="ENG+",
            direction="bullish",
            started_at=base + timedelta(hours=index - 1),
            ended_at=base + timedelta(hours=index),
            confirmed_at=None,
            confirmation_status="unknown",
            candle_timestamps=(
                base + timedelta(hours=index - 1),
                base + timedelta(hours=index),
            ),
            price_anchor=Decimal("99"),
            context="neutral",
            reasons=("test",),
            geometric_score=Decimal(str(index % 5)),
        )
        for index in range(20)
    )

    first = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        candlestick_patterns=patterns,
    )
    second = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        candlestick_patterns=patterns,
    )

    assert len(first.candlestick_patterns) <= 12
    assert first.candlestick_patterns == second.candlestick_patterns


def test_build_chart_render_model_places_pattern_marker_on_pattern_end_candle() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    ended_at = datetime(2026, 7, 21, 1, 0, tzinfo=UTC)
    patterns = (
        ChartCandlestickPattern(
            pattern_id="pat-1",
            pattern_type="bullish_engulfing",
            short_label="ENG+",
            direction="bullish",
            started_at=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            ended_at=ended_at,
            confirmed_at=None,
            confirmation_status="unknown",
            candle_timestamps=(
                datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                ended_at,
            ),
            price_anchor=Decimal("101"),
            context="neutral",
            reasons=("rule",),
            geometric_score=Decimal("0.9"),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        candlestick_patterns=patterns,
    )

    primitive_x = {primitive.opened_at: primitive.x_center for primitive in model.primitives}
    assert model.candlestick_patterns[0].ended_at == ended_at
    assert model.candlestick_patterns[0].x == primitive_x[ended_at]


def test_build_chart_render_model_prioritizes_multi_candle_patterns_deterministically() -> None:
    candles = _candles()
    viewport = ChartViewport.initial(total_candles=len(candles), visible_count=3)
    ended_at = datetime(2026, 7, 21, 2, 0, tzinfo=UTC)
    patterns = (
        ChartCandlestickPattern(
            pattern_id="short",
            pattern_type="hammer",
            short_label="HAM",
            direction="bullish",
            started_at=ended_at,
            ended_at=ended_at,
            confirmed_at=None,
            confirmation_status="unknown",
            candle_timestamps=(ended_at,),
            price_anchor=Decimal("101"),
            context="neutral",
            reasons=("r1",),
            geometric_score=Decimal("0.95"),
        ),
        ChartCandlestickPattern(
            pattern_id="long",
            pattern_type="bullish_three_line_strike",
            short_label="TLS+",
            direction="bullish",
            started_at=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
            ended_at=ended_at,
            confirmed_at=None,
            confirmation_status="unknown",
            candle_timestamps=(
                datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                ended_at,
            ),
            price_anchor=Decimal("100"),
            context="neutral",
            reasons=("r2",),
            geometric_score=Decimal("0.70"),
        ),
    )

    model = build_chart_render_model(
        candles=candles,
        width=900,
        height=400,
        viewport=viewport,
        candlestick_patterns=patterns,
    )

    assert model.candlestick_patterns[0].label == "TLS++1"


def test_chart_view_candlestick_pattern_toggle_is_independent_from_sr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)
    view = _view_stub(with_contract=True)
    view._show_support_resistance_var = _FakeBoolVar(False)
    view._show_candlestick_patterns_var = _FakeBoolVar(True)
    pattern_end = datetime(2026, 7, 21, 2, 0, tzinfo=UTC)
    view._contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
                support_resistance_zones=(
                    ChartSupportResistanceZone(
                        zone_type="support",
                        lower_price=Decimal("99"),
                        upper_price=Decimal("101"),
                        touch_count=2,
                        first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                        last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
                        pivot_ids=("p1",),
                    ),
                ),
                candlestick_patterns=(
                    ChartCandlestickPattern(
                        pattern_id="pat-1",
                        pattern_type="bullish_engulfing",
                        short_label="ENG+",
                        direction="bullish",
                        started_at=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                        ended_at=pattern_end,
                        confirmed_at=None,
                        confirmation_status="unknown",
                        candle_timestamps=(
                            datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                            pattern_end,
                        ),
                        price_anchor=Decimal("100"),
                        context="neutral",
                        reasons=("test",),
                        geometric_score=Decimal("0.8"),
                    ),
                ),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )

    view._render()
    assert any(text == "ENG+" for _, _, text in view._canvas.texts)

    view._show_candlestick_patterns_var = _FakeBoolVar(False)
    view._canvas.texts.clear()
    view._render()
    assert not any(text == "ENG+" for _, _, text in view._canvas.texts)


def test_chart_view_render_does_not_recompute_patterns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)

    def _raise_if_called(**_kwargs: object) -> tuple[object, ...]:
        message = "pattern detection must not run during chart render"
        raise AssertionError(message)

    monkeypatch.setattr(
        "elliottwaver.application.chart_contract.detect_candlestick_patterns",
        _raise_if_called,
    )

    view = _view_stub(with_contract=True)
    view._show_candlestick_patterns_var = _FakeBoolVar(True)
    view._contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
                candlestick_patterns=(
                    ChartCandlestickPattern(
                        pattern_id="pat-1",
                        pattern_type="bullish_engulfing",
                        short_label="ENG+",
                        direction="bullish",
                        started_at=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                        ended_at=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
                        confirmed_at=None,
                        confirmation_status="unknown",
                        candle_timestamps=(
                            datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                            datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
                        ),
                        price_anchor=Decimal("100"),
                        context="neutral",
                        reasons=("test",),
                        geometric_score=Decimal("0.8"),
                    ),
                ),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )

    view._render()
    view._render()

    assert any(text == "ENG+" for _, _, text in view._canvas.texts)


def test_chart_view_displays_candlestick_temporal_status_hint() -> None:
    view = _view_stub(with_contract=True)
    view._show_support_resistance_var = _FakeBoolVar(False)
    view._show_candlestick_patterns_var = _FakeBoolVar(True)
    pattern_end = datetime(2026, 7, 21, 2, 0, tzinfo=UTC)

    unknown_contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
                candlestick_patterns=(
                    ChartCandlestickPattern(
                        pattern_id="pat-1",
                        pattern_type="bullish_engulfing",
                        short_label="ENG+",
                        direction="bullish",
                        started_at=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                        ended_at=pattern_end,
                        confirmed_at=None,
                        confirmation_status="unknown",
                        candle_timestamps=(
                            datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                            pattern_end,
                        ),
                        price_anchor=Decimal("100"),
                        context="neutral",
                        reasons=("test",),
                        geometric_score=Decimal("0.8"),
                    ),
                ),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )
    view._contract = unknown_contract

    view._render()
    assert any(
        text
        == "Kerzenformationen: geometrische Erkennung - zeitliche Bestaetigung nicht verfuegbar."
        for _, _, text in view._canvas.texts
    )

    view._canvas.texts.clear()
    confirmed_contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
                candlestick_patterns=(
                    ChartCandlestickPattern(
                        pattern_id="pat-2",
                        pattern_type="bullish_engulfing",
                        short_label="ENG+",
                        direction="bullish",
                        started_at=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                        ended_at=pattern_end,
                        confirmed_at=datetime(2026, 7, 21, 3, 0, tzinfo=UTC),
                        confirmation_status="confirmed",
                        candle_timestamps=(
                            datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
                            pattern_end,
                        ),
                        price_anchor=Decimal("100"),
                        context="neutral",
                        reasons=("test",),
                        geometric_score=Decimal("0.8"),
                    ),
                ),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )
    view._contract = confirmed_contract

    view._render()
    assert any(
        text == "Kerzenformationen: geometrische Erkennung - zeitlich bestaetigt."
        for _, _, text in view._canvas.texts
    )


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


def test_chart_view_support_resistance_toggle_and_viewport_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)
    view = _view_stub(with_contract=True)
    view._show_support_resistance_var = _FakeBoolVar(True)
    view._contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
                support_resistance_zones=(
                    ChartSupportResistanceZone(
                        zone_type="support",
                        lower_price=Decimal("99"),
                        upper_price=Decimal("101"),
                        touch_count=2,
                        first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                        last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
                        pivot_ids=("p1", "p3"),
                    ),
                ),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )

    view._render()
    with_zones = len(view._canvas.rectangles)

    view._show_support_resistance_var = _FakeBoolVar(False)
    view._canvas.rectangles.clear()
    view._render()
    without_zones = len(view._canvas.rectangles)

    view.zoom_in()
    view.zoom_out()
    view.pan_left()
    view.pan_right()
    view.reset_view()

    assert with_zones == len(_candles()) + 1
    assert without_zones == len(_candles())


def test_chart_view_hides_support_resistance_labels_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)
    view = _view_stub(with_contract=True)
    view._show_support_resistance_var = _FakeBoolVar(True)
    view._contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
                support_resistance_zones=(
                    ChartSupportResistanceZone(
                        zone_type="support",
                        lower_price=Decimal("99"),
                        upper_price=Decimal("101"),
                        touch_count=2,
                        first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                        last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
                        pivot_ids=("p1", "p3"),
                    ),
                ),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )

    view._render()

    assert not any(text.startswith(("SUP x", "RES x")) for _, _, text in view._canvas.texts)


def test_chart_view_draws_zones_behind_candles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elliottwaver.interfaces.chart_tk._ensure_main_thread", lambda: None)
    view = _view_stub(with_contract=True)
    view._show_support_resistance_var = _FakeBoolVar(True)
    view._contract = ChartDataContract(
        symbol="EURUSD",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        timeframe_data=(
            TimeframeChartData(
                timeframe="1h",
                candles=tuple(sorted(_candles(), key=lambda candle: candle.opened_at)),
                swings=(),
                pivots=(),
                support_resistance_zones=(
                    ChartSupportResistanceZone(
                        zone_type="support",
                        lower_price=Decimal("99"),
                        upper_price=Decimal("101"),
                        touch_count=2,
                        first_timestamp=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
                        last_timestamp=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
                        pivot_ids=("p1", "p3"),
                    ),
                ),
            ),
        ),
        forecast_scenarios=(),
        fibonacci_projections=(),
    )

    view._render()

    assert "zone-rectangle" in view._canvas.operations
    assert "candle-rectangle" in view._canvas.operations
    assert view._canvas.operations.index("zone-rectangle") < view._canvas.operations.index(
        "candle-rectangle"
    )


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
