from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.confluence import (
    ConfluenceConflict,
    ConfluenceSeverity,
    MultiTimeframeConfluenceResult,
)
from elliottwaver.domain.detection import WaveCandidate
from elliottwaver.domain.market import Pivot, PivotType, Price, Swing
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType
from elliottwaver.domain.multi_timeframe import Timeframe
from elliottwaver.domain.rules.wave_rules import RuleResult, RuleViolation
from elliottwaver.domain.scoring import ScoreComponent, ScoredWaveCandidate, WaveScore
from elliottwaver.domain.selection import SelectedWaveCandidate, SelectionReason
from elliottwaver.domain.trend_hierarchy import (
    ParentChildRelation,
    RelationType,
    TrendHierarchy,
    TrendNode,
)

SYMBOL = Symbol("EURUSD")


def make_selected_wave_candidate(
    *,
    direction: str = "up",
    score_percent: str = "90",
    violations: int = 0,
    start: datetime | None = None,
) -> SelectedWaveCandidate:
    base_time = start or datetime(2026, 7, 20, 0, 0, tzinfo=UTC)

    if direction == "up":
        prices = ("100", "120", "108", "132", "121", "140")
        pivot_types = (
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
        )
    else:
        prices = ("140", "120", "132", "108", "121", "100")
        pivot_types = (
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
            PivotType.HIGH,
            PivotType.LOW,
        )

    pivots = tuple(
        Pivot(
            id=EntityId.new(),
            symbol=SYMBOL,
            timeframe=MarketTimeframe.ONE_HOUR,
            timestamp=base_time + timedelta(minutes=index * 30),
            price=Price.parse(price),
            pivot_type=pivot_type,
        )
        for index, (price, pivot_type) in enumerate(zip(prices, pivot_types, strict=True))
    )

    swings = tuple(
        Swing(id=EntityId.new(), start_pivot=pivots[index], end_pivot=pivots[index + 1])
        for index in range(5)
    )

    violations_tuple = tuple(
        RuleViolation(rule_name=f"rule_{index}", message="violation") for index in range(violations)
    )
    wave = Wave(
        id=EntityId.new(),
        wave_type=WaveType.IMPULSE,
        degree=WaveDegree.PRIMARY,
        swings=swings,
    )
    candidate = WaveCandidate(wave=wave, rule_result=RuleResult(violations=violations_tuple))

    percentage = Decimal(score_percent)
    score = WaveScore(
        total_score=percentage,
        components=(
            ScoreComponent(
                name="score",
                weight=Decimal("1"),
                value=percentage,
                max_value=Decimal("100"),
            ),
        ),
        percentage=percentage,
    )
    scored = ScoredWaveCandidate(candidate=candidate, score=score)
    reason = SelectionReason(
        policy_name="top_score",
        reason_code="highest_score",
        message="Selected highest scored candidate",
    )
    return SelectedWaveCandidate(scored_candidate=scored, reasons=(reason,), rank=1)


def make_trend_hierarchy(
    *,
    root_direction: str = "up",
    child_direction: str = "up",
    valid: bool = True,
) -> TrendHierarchy:
    root_time = datetime(2026, 7, 20, 0, 0, tzinfo=UTC)
    child_time = datetime(2026, 7, 20, 2, 0, tzinfo=UTC)

    root_timeframe = Timeframe.parse("D1")
    child_timeframe = Timeframe.parse("H4")

    root = TrendNode(
        timeframe=root_timeframe,
        selected_wave_candidate=make_selected_wave_candidate(
            direction=root_direction,
            score_percent="95",
            start=root_time,
        ),
        parent_timeframe=None,
        child_timeframes=(child_timeframe,) if valid else (),
        depth=0,
        analysed_at=root_time,
    )
    child = TrendNode(
        timeframe=child_timeframe,
        selected_wave_candidate=make_selected_wave_candidate(
            direction=child_direction,
            score_percent="85",
            start=child_time,
        ),
        parent_timeframe=root_timeframe,
        child_timeframes=(),
        depth=1,
        analysed_at=child_time,
    )

    relations = (
        ParentChildRelation(
            parent_timeframe=root_timeframe,
            child_timeframe=child_timeframe,
            relation_type=RelationType.PARENT,
            rationale="Derived from timeframe hierarchy order",
        ),
    )

    hierarchy = TrendHierarchy(nodes=(child, root), relations=relations)
    if valid:
        return hierarchy

    # Build a deterministically invalid hierarchy via consistency mismatch.
    invalid_root = TrendNode(
        timeframe=root_timeframe,
        selected_wave_candidate=root.selected_wave_candidate,
        parent_timeframe=None,
        child_timeframes=(),
        depth=0,
        analysed_at=root_time,
    )
    return TrendHierarchy(nodes=(child, invalid_root), relations=relations)


def make_confluence_result(
    *,
    confluence_percent: str,
    conflict_severity: ConfluenceSeverity | None = None,
) -> MultiTimeframeConfluenceResult:
    conflicts: tuple[ConfluenceConflict, ...] = ()
    if conflict_severity is not None:
        conflicts = (
            ConfluenceConflict(
                rule_name="test_rule",
                conflict_code="test_conflict",
                message="test conflict",
                severity=conflict_severity,
            ),
        )

    percent = Decimal(confluence_percent)
    return MultiTimeframeConfluenceResult(
        relation_results=(),
        analyzed_relations_count=0,
        confluence_score=percent,
        maximum_confluence_score=Decimal("100"),
        confluence_percent=percent,
        evidences=(),
        conflicts=conflicts,
        hierarchy_validation_result=None,
    )
