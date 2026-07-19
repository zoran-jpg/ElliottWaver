from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TypedDict

import pytest

from elliottwaver.core.market import Symbol
from elliottwaver.core.market import Timeframe as MarketTimeframe
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.domain.confluence import (
    CONFLICT_DIRECTION,
    CONFLICT_HIERARCHY_INVALID,
    CONFLICT_SCORE_THRESHOLD_NOT_REACHED,
    CONFLICT_STRUCTURAL_RELATION_INVALID,
    CONFLICT_TEMPORAL_CONTAINMENT_MISSING,
    EVIDENCE_DIRECTION_ALIGNED,
    EVIDENCE_SCORE_THRESHOLDS_REACHED,
    EVIDENCE_STRUCTURAL_RELATION_VALID,
    EVIDENCE_TEMPORALLY_CONTAINED,
    ConfluenceConfig,
    ConfluenceConflict,
    ConfluenceEvidence,
    ConfluenceRuleResult,
    ConfluenceSeverity,
    DirectionAlignmentRule,
    MultiTimeframeConfluenceAnalyzer,
    MultiTimeframeConfluenceResult,
    RelationConfluenceResult,
    ScoreSupportRule,
    StructuralContinuityRule,
    TemporalContainmentRule,
)
from elliottwaver.domain.detection.wave_detector import WaveCandidate
from elliottwaver.domain.market import Price
from elliottwaver.domain.market.pivot import Pivot, PivotType
from elliottwaver.domain.market.swing import Swing
from elliottwaver.domain.market.wave import Wave, WaveDegree, WaveType
from elliottwaver.domain.multi_timeframe import Timeframe
from elliottwaver.domain.rules.wave_rules import RuleResult
from elliottwaver.domain.scoring import ScoreComponent, ScoredWaveCandidate, WaveScore
from elliottwaver.domain.selection import SelectedWaveCandidate, SelectionReason
from elliottwaver.domain.trend_hierarchy import (
    ParentChildRelation,
    RelationType,
    TrendHierarchy,
    TrendNode,
)

_REASON_HIGHEST_SCORE = "highest_score"


class EvidenceKwargs(TypedDict):
    rule_name: str
    evidence_code: str
    message: str
    weight: Decimal


class ConflictKwargs(TypedDict):
    rule_name: str
    conflict_code: str
    message: str
    severity: ConfluenceSeverity


def make_selected_wave_candidate(
    *,
    direction: str = "up",
    score_percent: str = "90",
    start: datetime,
    pivot_spacing: timedelta = timedelta(hours=1),
    symbol: str = "EURUSD",
) -> SelectedWaveCandidate:
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
            symbol=Symbol(symbol),
            timeframe=MarketTimeframe.ONE_HOUR,
            timestamp=start + pivot_spacing * index,
            price=Price.parse(price),
            pivot_type=pivot_type,
        )
        for index, (price, pivot_type) in enumerate(zip(prices, pivot_types, strict=True))
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

    percentage = Decimal(score_percent)
    component = ScoreComponent(
        name="score",
        weight=Decimal("1"),
        value=percentage,
        max_value=Decimal("100"),
    )
    score = WaveScore(
        total_score=percentage,
        components=(component,),
        percentage=percentage,
    )
    scored = ScoredWaveCandidate(candidate=candidate, score=score)
    reason = SelectionReason(
        policy_name="top_score",
        reason_code=_REASON_HIGHEST_SCORE,
        message="Selected highest scored candidate",
    )
    return SelectedWaveCandidate(scored_candidate=scored, reasons=(reason,), rank=1)


def make_trend_node(
    *,
    timeframe: str,
    direction: str,
    start: datetime,
    score_percent: str,
    pivot_spacing: timedelta = timedelta(hours=1),
    parent_timeframe: Timeframe | None = None,
    child_timeframes: tuple[Timeframe, ...] = (),
    depth: int = 0,
    symbol: str = "EURUSD",
) -> TrendNode:
    return TrendNode(
        timeframe=Timeframe.parse(timeframe),
        selected_wave_candidate=make_selected_wave_candidate(
            direction=direction,
            score_percent=score_percent,
            start=start,
            pivot_spacing=pivot_spacing,
            symbol=symbol,
        ),
        parent_timeframe=parent_timeframe,
        child_timeframes=child_timeframes,
        depth=depth,
        analysed_at=start,
    )


def make_relation(
    parent_timeframe: str,
    child_timeframe: str,
    *,
    relation_type: RelationType = RelationType.PARENT,
    rationale: str = "Derived from timeframe hierarchy order",
) -> ParentChildRelation:
    return ParentChildRelation(
        parent_timeframe=Timeframe.parse(parent_timeframe),
        child_timeframe=Timeframe.parse(child_timeframe),
        relation_type=relation_type,
        rationale=rationale,
    )


def make_invalid_same_timeframe_relation() -> ParentChildRelation:
    relation = object.__new__(ParentChildRelation)
    object.__setattr__(relation, "parent_timeframe", Timeframe.parse("D1"))
    object.__setattr__(relation, "child_timeframe", Timeframe.parse("D1"))
    object.__setattr__(relation, "relation_type", RelationType.PARENT)
    object.__setattr__(relation, "rationale", "invalid")
    return relation


def make_valid_hierarchy() -> TrendHierarchy:
    root = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="95",
        pivot_spacing=timedelta(hours=2),
        parent_timeframe=None,
        child_timeframes=(Timeframe.parse("H4"),),
        depth=0,
    )
    child = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframes=(Timeframe.parse("H1"),),
        depth=1,
    )
    leaf = make_trend_node(
        timeframe="H1",
        direction="up",
        start=datetime(2026, 7, 19, 3, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(minutes=24),
        parent_timeframe=Timeframe.parse("H4"),
        child_timeframes=(),
        depth=2,
    )
    relations = (
        make_relation("D1", "H4"),
        make_relation("H4", "H1"),
    )
    return TrendHierarchy(nodes=(leaf, child, root), relations=relations)


def make_mixed_hierarchy() -> TrendHierarchy:
    root = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="95",
        pivot_spacing=timedelta(hours=2),
        parent_timeframe=None,
        child_timeframes=(Timeframe.parse("H4"),),
        depth=0,
    )
    child = make_trend_node(
        timeframe="H4",
        direction="down",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="60",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframes=(Timeframe.parse("H1"),),
        depth=1,
    )
    leaf = make_trend_node(
        timeframe="H1",
        direction="down",
        start=datetime(2026, 7, 19, 3, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(minutes=24),
        parent_timeframe=Timeframe.parse("H4"),
        child_timeframes=(),
        depth=2,
    )
    relations = (
        make_relation("D1", "H4"),
        make_relation("H4", "H1"),
    )
    return TrendHierarchy(nodes=(leaf, child, root), relations=relations)


def make_relation_result(
    *,
    relation: ParentChildRelation,
    parent_node: TrendNode | None,
    child_node: TrendNode | None,
    evidences: tuple[ConfluenceEvidence, ...] = (),
    conflicts: tuple[ConfluenceConflict, ...] = (),
    score: str = "0",
    max_score: str = "100",
    percent: str = "0",
    maximum_percent: str = "100",
) -> RelationConfluenceResult:
    return RelationConfluenceResult(
        relation=relation,
        parent_node=parent_node,
        child_node=child_node,
        evidences=evidences,
        conflicts=conflicts,
        confluence_score=Decimal(score),
        maximum_confluence_score=Decimal(max_score),
        confluence_percent=Decimal(percent),
        maximum_confluence_percent=Decimal(maximum_percent),
    )


def make_evidence(
    *,
    rule_name: str,
    code: str,
    weight: str,
    measured_value: object | None = None,
    expected_value: object | None = None,
) -> ConfluenceEvidence:
    return ConfluenceEvidence(
        rule_name=rule_name,
        evidence_code=code,
        message=f"{rule_name}:{code}",
        weight=Decimal(weight),
        measured_value=measured_value,
        expected_value=expected_value,
    )


def make_conflict(
    *,
    rule_name: str,
    code: str,
    severity: ConfluenceSeverity,
    measured_value: object | None = None,
    expected_value: object | None = None,
) -> ConfluenceConflict:
    return ConfluenceConflict(
        rule_name=rule_name,
        conflict_code=code,
        message=f"{rule_name}:{code}",
        severity=severity,
        measured_value=measured_value,
        expected_value=expected_value,
    )


def make_rule_result(
    *,
    evidence: ConfluenceEvidence | None = None,
    conflict: ConfluenceConflict | None = None,
    maximum_score: str = "25",
) -> ConfluenceRuleResult:
    evidences = (evidence,) if evidence is not None else ()
    conflicts = (conflict,) if conflict is not None else ()
    return ConfluenceRuleResult(
        evidences=evidences,
        conflicts=conflicts,
        maximum_score=Decimal(maximum_score),
    )


def test_confluence_config_valid_invalid_and_immutable() -> None:
    config = ConfluenceConfig(
        minimum_parent_score_percent=Decimal("65"),
        minimum_child_score_percent=Decimal("60"),
        evidence_weight_direction=Decimal("20"),
        evidence_weight_temporal=Decimal("30"),
        evidence_weight_structure=Decimal("25"),
        evidence_weight_score=Decimal("25"),
        maximum_confluence_percent=Decimal("100"),
    )

    assert config.minimum_parent_score_percent == Decimal("65")

    with pytest.raises(FrozenInstanceError):
        config.__setattr__("minimum_parent_score_percent", Decimal("50"))

    with pytest.raises(DomainError, match="finite"):
        ConfluenceConfig(minimum_parent_score_percent=Decimal("NaN"))

    with pytest.raises(DomainError, match=r"within \[0, 100\]"):
        ConfluenceConfig(minimum_child_score_percent=Decimal("101"))

    with pytest.raises(DomainError, match=r"within \[0, 100\]"):
        ConfluenceConfig(evidence_weight_direction=Decimal("-1"))

    with pytest.raises(DomainError, match="maximum_confluence_percent"):
        ConfluenceConfig(maximum_confluence_percent=Decimal("0"))


def test_confluence_evidence_valid_stable_code_and_immutability() -> None:
    evidence = ConfluenceEvidence(
        rule_name="direction_alignment_rule",
        evidence_code=EVIDENCE_DIRECTION_ALIGNED,
        message="Direction aligned",
        weight=Decimal("25"),
        measured_value=("up", "up"),
        expected_value="matching directions",
    )

    assert evidence.evidence_code == EVIDENCE_DIRECTION_ALIGNED
    assert evidence.weight == Decimal("25")

    with pytest.raises(FrozenInstanceError):
        evidence.__setattr__("message", "changed")

    with pytest.raises(DomainError, match="non-negative"):
        ConfluenceEvidence(
            rule_name="direction_alignment_rule",
            evidence_code=EVIDENCE_DIRECTION_ALIGNED,
            message="Direction aligned",
            weight=Decimal("-1"),
        )


def test_confluence_conflict_valid_severity_stable_code_and_immutability() -> None:
    conflict = ConfluenceConflict(
        rule_name="direction_alignment_rule",
        conflict_code=CONFLICT_DIRECTION,
        message="Direction conflict",
        severity=ConfluenceSeverity.CRITICAL,
        measured_value=("up", "down"),
        expected_value="matching directions",
    )

    assert conflict.conflict_code == CONFLICT_DIRECTION
    assert conflict.severity is ConfluenceSeverity.CRITICAL

    with pytest.raises(FrozenInstanceError):
        conflict.__setattr__("severity", ConfluenceSeverity.INFO)


@pytest.mark.parametrize(
    ("config_kwargs", "message_pattern"),
    [
        ({"evidence_weight_temporal": Decimal("-1")}, r"evidence_weight_temporal"),
        ({"evidence_weight_structure": Decimal("101")}, r"evidence_weight_structure"),
        ({"evidence_weight_score": Decimal("-1")}, r"evidence_weight_score"),
        ({"maximum_confluence_percent": Decimal("101")}, r"maximum_confluence_percent"),
        (
            {
                "evidence_weight_direction": Decimal("0"),
                "evidence_weight_temporal": Decimal("0"),
                "evidence_weight_structure": Decimal("0"),
                "evidence_weight_score": Decimal("0"),
            },
            r"At least one confluence evidence weight must be positive",
        ),
    ],
)
def test_confluence_config_rejects_invalid_weights_and_ranges(
    config_kwargs: dict[str, Decimal],
    message_pattern: str,
) -> None:
    with pytest.raises(DomainError, match=message_pattern):
        ConfluenceConfig(**config_kwargs)


@pytest.mark.parametrize(
    ("factory_kwargs", "message_pattern"),
    [
        (
            {
                "rule_name": "",
                "evidence_code": EVIDENCE_DIRECTION_ALIGNED,
                "message": "x",
                "weight": Decimal("1"),
            },
            r"rule_name must not be empty",
        ),
        (
            {"rule_name": "rule", "evidence_code": "", "message": "x", "weight": Decimal("1")},
            r"evidence_code must not be empty",
        ),
        (
            {
                "rule_name": "rule",
                "evidence_code": EVIDENCE_DIRECTION_ALIGNED,
                "message": "",
                "weight": Decimal("1"),
            },
            r"message must not be empty",
        ),
        (
            {
                "rule_name": "rule",
                "evidence_code": EVIDENCE_DIRECTION_ALIGNED,
                "message": "x",
                "weight": Decimal("-1"),
            },
            r"non-negative",
        ),
    ],
)
def test_confluence_evidence_validation(
    factory_kwargs: EvidenceKwargs,
    message_pattern: str,
) -> None:
    with pytest.raises(DomainError, match=message_pattern):
        ConfluenceEvidence(**factory_kwargs)


@pytest.mark.parametrize(
    ("factory_kwargs", "message_pattern"),
    [
        (
            {
                "rule_name": "",
                "conflict_code": CONFLICT_DIRECTION,
                "message": "x",
                "severity": ConfluenceSeverity.INFO,
            },
            r"rule_name must not be empty",
        ),
        (
            {
                "rule_name": "rule",
                "conflict_code": "",
                "message": "x",
                "severity": ConfluenceSeverity.INFO,
            },
            r"conflict_code must not be empty",
        ),
        (
            {
                "rule_name": "rule",
                "conflict_code": CONFLICT_DIRECTION,
                "message": "",
                "severity": ConfluenceSeverity.INFO,
            },
            r"message must not be empty",
        ),
    ],
)
def test_confluence_conflict_validation(
    factory_kwargs: ConflictKwargs,
    message_pattern: str,
) -> None:
    with pytest.raises(DomainError, match=message_pattern):
        ConfluenceConflict(**factory_kwargs)


def test_confluence_rule_result_validation_and_duplicate_codes() -> None:
    evidence = make_evidence(
        rule_name="direction_alignment_rule",
        code=EVIDENCE_DIRECTION_ALIGNED,
        weight="25",
    )
    conflict = make_conflict(
        rule_name="direction_alignment_rule",
        code=CONFLICT_DIRECTION,
        severity=ConfluenceSeverity.INFO,
    )

    with pytest.raises(DomainError, match="non-negative"):
        ConfluenceRuleResult(maximum_score=Decimal("-1"))

    with pytest.raises(DomainError, match="Duplicate evidence codes"):
        ConfluenceRuleResult(evidences=(evidence, evidence), maximum_score=Decimal("25"))

    with pytest.raises(DomainError, match="Duplicate conflict codes"):
        ConfluenceRuleResult(conflicts=(conflict, conflict), maximum_score=Decimal("25"))


def test_multi_timeframe_confluence_analyzer_requires_at_least_one_rule() -> None:
    with pytest.raises(DomainError, match="At least one confluence rule"):
        MultiTimeframeConfluenceAnalyzer(rules=())


def test_direction_alignment_rule_same_and_opposite_direction() -> None:
    config = ConfluenceConfig()
    rule = DirectionAlignmentRule()
    relation = make_relation("D1", "H4")
    parent = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    child = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )
    opposite = make_trend_node(
        timeframe="H4",
        direction="down",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )

    aligned_result = rule.evaluate(relation, parent, child, config)
    opposite_result = rule.evaluate(relation, parent, opposite, config)

    assert aligned_result.evidences[0].evidence_code == EVIDENCE_DIRECTION_ALIGNED
    assert opposite_result.conflicts[0].conflict_code == CONFLICT_DIRECTION
    assert parent.selected_wave_candidate.wave_candidate.wave.direction.value == "up"
    assert child.selected_wave_candidate.wave_candidate.wave.direction.value == "up"


def test_temporal_containment_rule_boundaries_and_overlap() -> None:
    config = ConfluenceConfig()
    rule = TemporalContainmentRule()
    relation = make_relation("D1", "H4")
    parent = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    contained = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )
    identical = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=2),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )
    partial = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 8, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )
    outside = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 12, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )

    assert (
        rule.evaluate(relation, parent, contained, config).evidences[0].evidence_code
        == EVIDENCE_TEMPORALLY_CONTAINED
    )
    assert (
        rule.evaluate(relation, parent, identical, config).evidences[0].evidence_code
        == EVIDENCE_TEMPORALLY_CONTAINED
    )
    partial_result = rule.evaluate(relation, parent, partial, config)
    outside_result = rule.evaluate(relation, parent, outside, config)

    assert partial_result.conflicts[0].conflict_code == CONFLICT_TEMPORAL_CONTAINMENT_MISSING
    assert partial_result.conflicts[0].severity is ConfluenceSeverity.WARNING
    assert outside_result.conflicts[0].severity is ConfluenceSeverity.CRITICAL


@pytest.mark.parametrize(
    ("relation", "parent_symbol", "child_symbol", "expected_code"),
    [
        (make_relation("D1", "H4"), "EURUSD", "EURUSD", EVIDENCE_STRUCTURAL_RELATION_VALID),
        (make_relation("D1", "H4"), "EURUSD", "GBPUSD", CONFLICT_STRUCTURAL_RELATION_INVALID),
        (make_relation("H4", "D1"), "EURUSD", "EURUSD", CONFLICT_STRUCTURAL_RELATION_INVALID),
    ],
)
def test_structural_continuity_rule_compatibility(
    relation: ParentChildRelation,
    parent_symbol: str,
    child_symbol: str,
    expected_code: str,
) -> None:
    config = ConfluenceConfig()
    rule = StructuralContinuityRule()
    parent = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        symbol=parent_symbol,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    child = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
        symbol=child_symbol,
    )

    result = rule.evaluate(relation, parent, child, config)

    if expected_code == EVIDENCE_STRUCTURAL_RELATION_VALID:
        assert result.evidences[0].evidence_code == expected_code
    else:
        assert result.conflicts[0].conflict_code == expected_code


def test_structural_continuity_rule_self_relation_and_node_reference_mismatch() -> None:
    config = ConfluenceConfig()
    rule = StructuralContinuityRule()
    self_relation = make_invalid_same_timeframe_relation()
    parent = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    child = make_trend_node(
        timeframe="M15",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )

    result_self = rule.evaluate(self_relation, parent, parent, config)
    result_mismatch = rule.evaluate(make_relation("D1", "H4"), parent, child, config)

    assert result_self.conflicts[0].conflict_code == CONFLICT_STRUCTURAL_RELATION_INVALID
    assert result_mismatch.conflicts[0].conflict_code == CONFLICT_STRUCTURAL_RELATION_INVALID


def test_score_support_rule_thresholds_and_no_recomputation() -> None:
    config = ConfluenceConfig(
        minimum_parent_score_percent=Decimal("70"),
        minimum_child_score_percent=Decimal("70"),
        evidence_weight_score=Decimal("25"),
    )
    rule = ScoreSupportRule()
    relation = make_relation("D1", "H4")
    parent = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="70",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    child = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="70",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )
    parent_low = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="69",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    child_low = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="69",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )

    both = rule.evaluate(relation, parent, child, config)
    only_parent = rule.evaluate(relation, parent, child_low, config)
    only_child = rule.evaluate(relation, parent_low, child, config)
    none = rule.evaluate(relation, parent_low, child_low, config)

    assert both.evidences[0].evidence_code == EVIDENCE_SCORE_THRESHOLDS_REACHED
    assert only_parent.conflicts[0].conflict_code == CONFLICT_SCORE_THRESHOLD_NOT_REACHED
    assert only_child.conflicts[0].conflict_code == CONFLICT_SCORE_THRESHOLD_NOT_REACHED
    assert none.conflicts[0].conflict_code == CONFLICT_SCORE_THRESHOLD_NOT_REACHED
    assert parent.selected_wave_candidate.wave_score.percentage == Decimal("70")


def test_relation_confluence_result_scoring_and_is_confluent() -> None:
    relation = make_relation("D1", "H4")
    parent = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    child = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        depth=1,
    )
    evidence = make_evidence(
        rule_name="direction_alignment_rule",
        code=EVIDENCE_DIRECTION_ALIGNED,
        weight="25",
        measured_value=("up", "up"),
        expected_value="matching directions",
    )
    child_range = (
        child.selected_wave_candidate.wave_candidate.wave.start_timestamp,
        child.selected_wave_candidate.wave_candidate.wave.end_timestamp,
    )
    parent_range = (
        parent.selected_wave_candidate.wave_candidate.wave.start_timestamp,
        parent.selected_wave_candidate.wave_candidate.wave.end_timestamp,
    )
    warning = make_conflict(
        rule_name="temporal_containment_rule",
        code=CONFLICT_TEMPORAL_CONTAINMENT_MISSING,
        severity=ConfluenceSeverity.WARNING,
        measured_value=child_range,
        expected_value=parent_range,
    )
    critical = make_conflict(
        rule_name="structural_continuity_rule",
        code=CONFLICT_STRUCTURAL_RELATION_INVALID,
        severity=ConfluenceSeverity.CRITICAL,
    )

    only_evidence = make_relation_result(
        relation=relation,
        parent_node=parent,
        child_node=child,
        evidences=(evidence,),
        score="25",
        max_score="100",
        percent="25",
    )
    mixed = make_relation_result(
        relation=relation,
        parent_node=parent,
        child_node=child,
        evidences=(evidence,),
        conflicts=(warning,),
        score="25",
        max_score="100",
        percent="25",
    )
    blocked = make_relation_result(
        relation=relation,
        parent_node=parent,
        child_node=child,
        evidences=(evidence,),
        conflicts=(critical,),
        score="25",
        max_score="100",
        percent="25",
    )

    assert only_evidence.is_confluent is True
    assert mixed.is_confluent is True
    assert blocked.is_confluent is False
    assert only_evidence.evidence_count == 1
    assert only_evidence.conflict_count == 0

    with pytest.raises(DomainError, match="Duplicate evidence codes"):
        make_relation_result(
            relation=relation,
            parent_node=parent,
            child_node=child,
            evidences=(evidence, evidence),
            score="50",
            max_score="100",
            percent="50",
        )


def test_multi_timeframe_confluence_result_empty_and_aggregation() -> None:
    empty = MultiTimeframeConfluenceResult.from_relation_results(
        relation_results=(),
        hierarchy_validation_result=TrendHierarchy().validation,
        maximum_confluence_percent=Decimal("100"),
    )

    relation_one = make_relation("D1", "H4")
    relation_two = make_relation("H4", "H1")
    parent = make_trend_node(
        timeframe="D1",
        direction="up",
        start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        score_percent="90",
        pivot_spacing=timedelta(hours=2),
        depth=0,
        child_timeframes=(Timeframe.parse("H4"),),
    )
    child = make_trend_node(
        timeframe="H4",
        direction="up",
        start=datetime(2026, 7, 19, 2, 0, tzinfo=UTC),
        score_percent="85",
        pivot_spacing=timedelta(hours=1),
        parent_timeframe=Timeframe.parse("D1"),
        child_timeframes=(Timeframe.parse("H1"),),
        depth=1,
    )
    leaf = make_trend_node(
        timeframe="H1",
        direction="up",
        start=datetime(2026, 7, 19, 3, 0, tzinfo=UTC),
        score_percent="80",
        pivot_spacing=timedelta(minutes=24),
        parent_timeframe=Timeframe.parse("H4"),
        depth=2,
    )
    evidence = make_evidence(
        rule_name="direction_alignment_rule",
        code=EVIDENCE_DIRECTION_ALIGNED,
        weight="25",
    )
    result_one = make_relation_result(
        relation=relation_one,
        parent_node=parent,
        child_node=child,
        evidences=(evidence,),
        score="25",
        max_score="100",
        percent="25",
    )
    result_two = make_relation_result(
        relation=relation_two,
        parent_node=child,
        child_node=leaf,
        evidences=(evidence,),
        score="25",
        max_score="100",
        percent="25",
    )
    multi_hierarchy = TrendHierarchy(
        nodes=(leaf, child, parent),
        relations=(relation_one, relation_two),
    )
    multi = MultiTimeframeConfluenceResult.from_relation_results(
        relation_results=(result_two, result_one),
        hierarchy_validation_result=multi_hierarchy.validation,
        maximum_confluence_percent=Decimal("100"),
    )

    assert empty.is_empty is True
    assert empty.strongest_relation is None
    assert empty.weakest_relation is None

    assert multi.is_empty is False
    assert multi.analyzed_relations_count == 2
    assert multi.confluence_count == 2
    assert multi.conflict_count == 0
    assert multi.strongest_relation == result_one
    assert multi.weakest_relation == result_one
    assert multi.confluence_percent == Decimal("25")
    assert multi.evidences == (evidence, evidence)


def test_multi_timeframe_confluence_analyzer_empty_single_valid_and_invalid_hierarchy() -> None:
    analyzer = MultiTimeframeConfluenceAnalyzer()

    empty_result = analyzer.analyze(TrendHierarchy())
    single_result = analyzer.analyze(
        TrendHierarchy(
            nodes=(
                make_trend_node(
                    timeframe="D1",
                    direction="up",
                    start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
                    score_percent="90",
                    pivot_spacing=timedelta(hours=2),
                    depth=0,
                ),
            )
        )
    )
    valid_result = analyzer.analyze(make_valid_hierarchy())
    invalid_result = analyzer.analyze(
        TrendHierarchy(
            nodes=(
                make_trend_node(
                    timeframe="H1",
                    direction="up",
                    start=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
                    score_percent="90",
                    pivot_spacing=timedelta(hours=1),
                    depth=0,
                ),
                make_trend_node(
                    timeframe="H1",
                    direction="down",
                    start=datetime(2026, 7, 19, 1, 0, tzinfo=UTC),
                    score_percent="85",
                    pivot_spacing=timedelta(hours=1),
                    depth=0,
                ),
            )
        )
    )

    assert empty_result.is_empty is True
    assert single_result.is_empty is True
    assert valid_result.analyzed_relations_count == 2
    assert valid_result.has_conflicts is False
    assert valid_result.confluence_count == 2
    assert invalid_result.hierarchy_validation_result is not None
    assert invalid_result.hierarchy_validation_result.is_valid is False
    assert invalid_result.has_conflicts is True
    assert any(
        conflict.conflict_code == CONFLICT_HIERARCHY_INVALID
        for conflict in invalid_result.conflicts
    )


def test_multi_timeframe_confluence_analyzer_deterministic_and_unchanged_inputs() -> None:
    analyzer = MultiTimeframeConfluenceAnalyzer()
    hierarchy = make_valid_hierarchy()
    before_nodes = hierarchy.nodes
    before_relations = hierarchy.relations

    first = analyzer.analyze(hierarchy)
    second = analyzer.analyze(hierarchy)

    assert first == second
    assert hierarchy.nodes == before_nodes
    assert hierarchy.relations == before_relations
    assert first.analyzed_relations_count == len(hierarchy.relations)


def test_multi_timeframe_confluence_analyzer_executes_rules_deterministically() -> None:
    calls: list[tuple[str, str, str]] = []

    class RecordingRule:
        def __init__(self, name: str) -> None:
            self.name = name

        def evaluate(
            self,
            relation: ParentChildRelation,
            _parent_node: TrendNode | None,
            _child_node: TrendNode | None,
            _config: ConfluenceConfig,
        ) -> ConfluenceRuleResult:
            calls.append(
                (self.name, relation.parent_timeframe.value, relation.child_timeframe.value)
            )
            return ConfluenceRuleResult(maximum_score=Decimal("1"))

    analyzer = MultiTimeframeConfluenceAnalyzer(
        rules=(RecordingRule("rule_a"), RecordingRule("rule_b")),
    )
    analyzer.analyze(make_valid_hierarchy())

    assert calls == [
        ("rule_a", "D1", "H4"),
        ("rule_b", "D1", "H4"),
        ("rule_a", "H4", "H1"),
        ("rule_b", "H4", "H1"),
    ]


def test_multi_timeframe_confluence_analyzer_does_not_recompute_wave_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hierarchy = make_valid_hierarchy()

    def raise_on_recompute(*_args: object, **_kwargs: object) -> WaveScore:
        message = "wave scores must not be recomputed"
        raise RuntimeError(message)

    monkeypatch.setattr(WaveScore, "from_components", raise_on_recompute)

    result = MultiTimeframeConfluenceAnalyzer().analyze(hierarchy)

    assert result.analyzed_relations_count == len(hierarchy.relations)
