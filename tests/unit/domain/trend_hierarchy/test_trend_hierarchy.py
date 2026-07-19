from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.detection.wave_detector import WaveCandidate
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType
from elliottwaver.domain.multi_timeframe import (
    MultiTimeframeAnalysis,
    Timeframe,
    TimeframeAnalysis,
)
from elliottwaver.domain.rules.wave_rules import RuleResult
from elliottwaver.domain.scoring import ScoreComponent, ScoredWaveCandidate, WaveScore
from elliottwaver.domain.selection import (
    SelectedWaveCandidate,
    SelectionReason,
    SelectionResult,
)
from elliottwaver.domain.trend_hierarchy import (
    HierarchyValidationResult,
    ParentChildRelation,
    RelationType,
    TrendHierarchy,
    TrendHierarchyBuilder,
    TrendNode,
)

_REASON_HIGHEST_SCORE = "highest_score"


def make_selected_wave_candidate(*, anchor: int = 0) -> SelectedWaveCandidate:
    base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC) + timedelta(days=anchor)
    prices = ("100", "120", "108", "132", "121", "140")

    pivots = tuple(
        Pivot(
            id=EntityId.new(),
            symbol=Symbol("EURUSD"),
            timeframe=MarketTimeframe.ONE_HOUR,
            timestamp=base + timedelta(hours=index),
            price=Price.parse(price),
            pivot_type=PivotType.LOW if index % 2 == 0 else PivotType.HIGH,
        )
        for index, price in enumerate(prices)
    )

    swings = tuple(
        Swing(id=EntityId.new(), start_pivot=pivots[index], end_pivot=pivots[index + 1])
        for index in range(5)
    )

    wave = Wave(
        id=EntityId.new(),
        wave_type=WaveType.IMPULSE,
        degree=WaveDegree.PRIMARY,
        swings=swings,
    )
    candidate = WaveCandidate(wave=wave, rule_result=RuleResult())

    component = ScoreComponent(
        name="score",
        weight=Decimal("1"),
        value=Decimal("90"),
        max_value=Decimal("100"),
    )
    score = WaveScore(
        total_score=Decimal("90"),
        components=(component,),
        percentage=Decimal("90"),
    )
    scored = ScoredWaveCandidate(candidate=candidate, score=score)

    reason = SelectionReason(
        policy_name="top_score",
        reason_code=_REASON_HIGHEST_SCORE,
        message="Selected highest scored candidate",
    )
    return SelectedWaveCandidate(scored_candidate=scored, reasons=(reason,), rank=1)


def make_selection_result(*, considered: int, has_selection: bool = True) -> SelectionResult:
    selected = (make_selected_wave_candidate(anchor=considered),) if has_selection else ()
    return SelectionResult(
        selected_candidates=selected,
        policy_name="top_score",
        considered_candidates=considered,
    )


def make_timeframe_analysis(
    *,
    timeframe: str,
    considered: int,
    has_selection: bool = True,
    analysed_at: datetime | None = None,
) -> TimeframeAnalysis:
    return TimeframeAnalysis(
        timeframe=Timeframe.parse(timeframe),
        selection_result=make_selection_result(
            considered=considered,
            has_selection=has_selection,
        ),
        analysed_at=analysed_at or datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
        symbol=Symbol("EURUSD"),
        analysed_candidates_count=considered,
    )


def test_trend_node_root_child_leaf_depth_and_immutability() -> None:
    root = TrendNode(
        timeframe=Timeframe.parse("D1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=1),
        parent_timeframe=None,
        child_timeframes=(Timeframe.parse("H4"),),
        depth=0,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    child = TrendNode(
        timeframe=Timeframe.parse("H4"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=2),
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframes=(),
        depth=1,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )

    assert root.is_root is True
    assert root.is_leaf is False
    assert child.is_root is False
    assert child.is_leaf is True
    assert child.depth == 1

    with pytest.raises(FrozenInstanceError):
        root.__setattr__("depth", 3)


def test_parent_child_relation_valid_equality_and_immutability() -> None:
    relation_one = ParentChildRelation(
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframe=Timeframe.parse("H4"),
        relation_type=RelationType.PARENT,
        rationale="Derived from timeframe hierarchy order",
    )
    relation_two = ParentChildRelation(
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframe=Timeframe.parse("H4"),
        relation_type=RelationType.PARENT,
        rationale="Derived from timeframe hierarchy order",
    )

    assert relation_one == relation_two

    with pytest.raises(FrozenInstanceError):
        relation_one.__setattr__("rationale", "changed")


def test_trend_hierarchy_empty_and_single_node_properties() -> None:
    empty = TrendHierarchy()

    assert empty.node_count == 0
    assert empty.depth == 0
    assert empty.root is None
    assert empty.leaf_nodes == ()

    single_node = TrendNode(
        timeframe=Timeframe.parse("D1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=1),
        parent_timeframe=None,
        child_timeframes=(),
        depth=0,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    single = TrendHierarchy(nodes=(single_node,))

    assert single.node_count == 1
    assert single.root == single_node
    assert single.leaf_nodes == (single_node,)
    assert single.depth == 0


def test_trend_hierarchy_multiple_nodes_root_leafs_depth_and_node_count() -> None:
    root = TrendNode(
        timeframe=Timeframe.parse("D1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=1),
        parent_timeframe=None,
        child_timeframes=(Timeframe.parse("H4"),),
        depth=0,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    child = TrendNode(
        timeframe=Timeframe.parse("H4"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=2),
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframes=(Timeframe.parse("H1"),),
        depth=1,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    leaf = TrendNode(
        timeframe=Timeframe.parse("H1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=3),
        parent_timeframe=Timeframe.parse("H4"),
        child_timeframes=(),
        depth=2,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )

    hierarchy = TrendHierarchy(nodes=(leaf, child, root))

    assert hierarchy.root == root
    assert hierarchy.leaf_nodes == (leaf,)
    assert hierarchy.depth == 2
    assert hierarchy.node_count == 3


def test_hierarchy_validation_result_valid_cycle_duplicate_multiple_roots_missing_parent() -> None:
    valid_root = TrendNode(
        timeframe=Timeframe.parse("D1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=1),
        parent_timeframe=None,
        child_timeframes=(Timeframe.parse("H4"),),
        depth=0,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    valid_child = TrendNode(
        timeframe=Timeframe.parse("H4"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=2),
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframes=(),
        depth=1,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    valid_hierarchy = TrendHierarchy(nodes=(valid_root, valid_child))
    valid_result = HierarchyValidationResult.evaluate(valid_hierarchy)
    assert valid_result.is_valid is True

    cycle_a = TrendNode(
        timeframe=Timeframe.parse("D1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=3),
        parent_timeframe=Timeframe.parse("H4"),
        child_timeframes=(Timeframe.parse("H4"),),
        depth=1,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    cycle_b = TrendNode(
        timeframe=Timeframe.parse("H4"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=4),
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframes=(Timeframe.parse("D1"),),
        depth=1,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    cycle_result = HierarchyValidationResult.evaluate(TrendHierarchy(nodes=(cycle_a, cycle_b)))
    assert cycle_result.has_cycle is True

    duplicate_one = TrendNode(
        timeframe=Timeframe.parse("H1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=5),
        parent_timeframe=None,
        child_timeframes=(),
        depth=0,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    duplicate_two = TrendNode(
        timeframe=Timeframe.parse("H1"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=6),
        parent_timeframe=None,
        child_timeframes=(),
        depth=0,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    duplicate_result = HierarchyValidationResult.evaluate(
        TrendHierarchy(nodes=(duplicate_one, duplicate_two))
    )
    assert duplicate_result.has_duplicate_timeframes is True

    multiple_roots_result = HierarchyValidationResult.evaluate(
        TrendHierarchy(nodes=(duplicate_one, valid_root))
    )
    assert multiple_roots_result.root_count > 1

    missing_parent = TrendNode(
        timeframe=Timeframe.parse("M15"),
        selected_wave_candidate=make_selected_wave_candidate(anchor=7),
        parent_timeframe=Timeframe.parse("M30"),
        child_timeframes=(),
        depth=1,
        analysed_at=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
    )
    missing_parent_result = HierarchyValidationResult.evaluate(
        TrendHierarchy(nodes=(missing_parent,))
    )
    assert missing_parent_result.has_missing_parent is True


def test_trend_hierarchy_builder_empty_single_multiple_deterministic_and_ordered() -> None:
    builder = TrendHierarchyBuilder()

    empty = builder.build(MultiTimeframeAnalysis())
    assert empty.node_count == 0

    single_analysis = MultiTimeframeAnalysis(
        analyses=(make_timeframe_analysis(timeframe="H1", considered=3),)
    )
    single_hierarchy = builder.build(single_analysis)
    assert single_hierarchy.node_count == 1
    assert single_hierarchy.root is not None

    multi_analysis = MultiTimeframeAnalysis(
        analyses=(
            make_timeframe_analysis(timeframe="M15", considered=1),
            make_timeframe_analysis(timeframe="D1", considered=4),
            make_timeframe_analysis(timeframe="H1", considered=2),
        )
    )
    first = builder.build(multi_analysis)
    second = builder.build(multi_analysis)

    assert first == second
    assert tuple(node.timeframe for node in first.nodes) == (
        Timeframe.parse("D1"),
        Timeframe.parse("H1"),
        Timeframe.parse("M15"),
    )
    assert first.is_valid is True


def test_builder_skips_timeframes_without_selection() -> None:
    builder = TrendHierarchyBuilder()

    analysis = MultiTimeframeAnalysis(
        analyses=(
            make_timeframe_analysis(timeframe="D1", considered=5, has_selection=True),
            make_timeframe_analysis(timeframe="H4", considered=3, has_selection=False),
            make_timeframe_analysis(timeframe="H1", considered=2, has_selection=True),
        )
    )

    hierarchy = builder.build(analysis)

    assert tuple(node.timeframe for node in hierarchy.nodes) == (
        Timeframe.parse("D1"),
        Timeframe.parse("H1"),
    )
