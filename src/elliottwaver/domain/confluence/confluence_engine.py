"""Multi-timeframe confluence evaluation over an existing trend hierarchy."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.domain.multi_timeframe import Timeframe
    from elliottwaver.domain.trend_hierarchy import (
        HierarchyValidationResult,
        ParentChildRelation,
        TrendHierarchy,
        TrendNode,
    )


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")

EVIDENCE_DIRECTION_ALIGNED = "direction_aligned"
EVIDENCE_TEMPORALLY_CONTAINED = "temporally_contained"
EVIDENCE_STRUCTURAL_RELATION_VALID = "structural_relation_valid"
EVIDENCE_SCORE_THRESHOLDS_REACHED = "score_thresholds_reached"

CONFLICT_DIRECTION = "direction_conflict"
CONFLICT_TEMPORAL_CONTAINMENT_MISSING = "temporal_containment_missing"
CONFLICT_STRUCTURAL_RELATION_INVALID = "structural_relation_invalid"
CONFLICT_SCORE_THRESHOLD_NOT_REACHED = "score_threshold_not_reached"
CONFLICT_HIERARCHY_INVALID = "hierarchy_invalid"


class ConfluenceSeverity(StrEnum):
    """Severity levels for confluence conflicts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ConfluenceConfig:
    """Centralized weights and thresholds for confluence evaluation."""

    minimum_parent_score_percent: Decimal = Decimal("70")
    minimum_child_score_percent: Decimal = Decimal("70")
    evidence_weight_direction: Decimal = Decimal("25")
    evidence_weight_temporal: Decimal = Decimal("25")
    evidence_weight_structure: Decimal = Decimal("25")
    evidence_weight_score: Decimal = Decimal("25")
    maximum_confluence_percent: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        numeric_fields = (
            self.minimum_parent_score_percent,
            self.minimum_child_score_percent,
            self.evidence_weight_direction,
            self.evidence_weight_temporal,
            self.evidence_weight_structure,
            self.evidence_weight_score,
            self.maximum_confluence_percent,
        )
        if not all(value.is_finite() for value in numeric_fields):
            message = "ConfluenceConfig values must be finite"
            raise DomainError(message)

        if not _ZERO <= self.minimum_parent_score_percent <= _HUNDRED:
            message = "minimum_parent_score_percent must be within [0, 100]"
            raise DomainError(message)

        if not _ZERO <= self.minimum_child_score_percent <= _HUNDRED:
            message = "minimum_child_score_percent must be within [0, 100]"
            raise DomainError(message)

        if not _ZERO <= self.evidence_weight_direction <= _HUNDRED:
            message = "evidence_weight_direction must be within [0, 100]"
            raise DomainError(message)

        if not _ZERO <= self.evidence_weight_temporal <= _HUNDRED:
            message = "evidence_weight_temporal must be within [0, 100]"
            raise DomainError(message)

        if not _ZERO <= self.evidence_weight_structure <= _HUNDRED:
            message = "evidence_weight_structure must be within [0, 100]"
            raise DomainError(message)

        if not _ZERO <= self.evidence_weight_score <= _HUNDRED:
            message = "evidence_weight_score must be within [0, 100]"
            raise DomainError(message)

        if self.maximum_confluence_percent <= _ZERO:
            message = "maximum_confluence_percent must be > 0"
            raise DomainError(message)

        if self.maximum_confluence_percent > _HUNDRED:
            message = "maximum_confluence_percent must be within (0, 100]"
            raise DomainError(message)

        if (
            self.evidence_weight_direction
            + self.evidence_weight_temporal
            + self.evidence_weight_structure
            + self.evidence_weight_score
        ) <= _ZERO:
            message = "At least one confluence evidence weight must be positive"
            raise DomainError(message)


@dataclass(frozen=True, slots=True)
class ConfluenceEvidence:
    """Positive confluence observation reported by a rule."""

    rule_name: str
    evidence_code: str
    message: str
    weight: Decimal
    measured_value: object | None = None
    expected_value: object | None = None

    def __post_init__(self) -> None:
        if not self.rule_name.strip():
            message = "rule_name must not be empty"
            raise DomainError(message)

        if not self.evidence_code.strip():
            message = "evidence_code must not be empty"
            raise DomainError(message)

        if not self.message.strip():
            message = "message must not be empty"
            raise DomainError(message)

        if not self.weight.is_finite() or self.weight < _ZERO:
            message = "weight must be finite and non-negative"
            raise DomainError(message)


@dataclass(frozen=True, slots=True)
class ConfluenceConflict:
    """Negative or neutral confluence observation reported by a rule."""

    rule_name: str
    conflict_code: str
    message: str
    severity: ConfluenceSeverity
    measured_value: object | None = None
    expected_value: object | None = None

    def __post_init__(self) -> None:
        if not self.rule_name.strip():
            message = "rule_name must not be empty"
            raise DomainError(message)

        if not self.conflict_code.strip():
            message = "conflict_code must not be empty"
            raise DomainError(message)

        if not self.message.strip():
            message = "message must not be empty"
            raise DomainError(message)


@dataclass(frozen=True, slots=True)
class ConfluenceRuleResult:
    """Result of a single confluence rule evaluation."""

    evidences: tuple[ConfluenceEvidence, ...] = ()
    conflicts: tuple[ConfluenceConflict, ...] = ()
    maximum_score: Decimal = _ZERO

    def __post_init__(self) -> None:
        if not self.maximum_score.is_finite() or self.maximum_score < _ZERO:
            message = "maximum_score must be finite and non-negative"
            raise DomainError(message)

        _validate_unique_rule_codes(self.evidences, self.conflicts)


@runtime_checkable
class ConfluenceRule(Protocol):
    """A single deterministic confluence rule."""

    name: str

    def evaluate(
        self,
        relation: ParentChildRelation,
        parent_node: TrendNode | None,
        child_node: TrendNode | None,
        config: ConfluenceConfig,
    ) -> ConfluenceRuleResult:
        """Evaluate a relation and return evidence or conflicts."""


@dataclass(frozen=True, slots=True)
class DirectionAlignmentRule:
    """Check whether parent and child waves move in the same direction."""

    name: str = "direction_alignment_rule"

    def evaluate(
        self,
        _relation: ParentChildRelation,
        parent_node: TrendNode | None,
        child_node: TrendNode | None,
        config: ConfluenceConfig,
    ) -> ConfluenceRuleResult:
        if parent_node is None or child_node is None:
            conflict = ConfluenceConflict(
                rule_name=self.name,
                conflict_code=CONFLICT_DIRECTION,
                message="Direction cannot be evaluated without both nodes",
                severity=ConfluenceSeverity.CRITICAL,
                measured_value=None,
                expected_value="both nodes present",
            )
            return ConfluenceRuleResult(
                conflicts=(conflict,),
                maximum_score=config.evidence_weight_direction,
            )

        parent_direction = parent_node.selected_wave_candidate.wave_candidate.wave.direction
        child_direction = child_node.selected_wave_candidate.wave_candidate.wave.direction

        if parent_direction == child_direction:
            evidence = ConfluenceEvidence(
                rule_name=self.name,
                evidence_code=EVIDENCE_DIRECTION_ALIGNED,
                message="Parent and child waves move in the same direction",
                weight=config.evidence_weight_direction,
                measured_value=(parent_direction.value, child_direction.value),
                expected_value="matching directions",
            )
            return ConfluenceRuleResult(
                evidences=(evidence,),
                maximum_score=config.evidence_weight_direction,
            )

        conflict = ConfluenceConflict(
            rule_name=self.name,
            conflict_code=CONFLICT_DIRECTION,
            message="Parent and child waves move in opposite directions",
            severity=ConfluenceSeverity.CRITICAL,
            measured_value=(parent_direction.value, child_direction.value),
            expected_value="matching directions",
        )
        return ConfluenceRuleResult(
            conflicts=(conflict,),
            maximum_score=config.evidence_weight_direction,
        )


@dataclass(frozen=True, slots=True)
class TemporalContainmentRule:
    """Check whether the child wave is fully contained in the parent wave time range."""

    name: str = "temporal_containment_rule"

    def evaluate(
        self,
        _relation: ParentChildRelation,
        parent_node: TrendNode | None,
        child_node: TrendNode | None,
        config: ConfluenceConfig,
    ) -> ConfluenceRuleResult:
        if parent_node is None or child_node is None:
            conflict = ConfluenceConflict(
                rule_name=self.name,
                conflict_code=CONFLICT_TEMPORAL_CONTAINMENT_MISSING,
                message="Temporal containment cannot be evaluated without both nodes",
                severity=ConfluenceSeverity.CRITICAL,
                measured_value=None,
                expected_value="both nodes present",
            )
            return ConfluenceRuleResult(
                conflicts=(conflict,),
                maximum_score=config.evidence_weight_temporal,
            )

        parent_start = parent_node.selected_wave_candidate.wave_candidate.wave.start_timestamp
        parent_end = parent_node.selected_wave_candidate.wave_candidate.wave.end_timestamp
        child_start = child_node.selected_wave_candidate.wave_candidate.wave.start_timestamp
        child_end = child_node.selected_wave_candidate.wave_candidate.wave.end_timestamp

        if parent_start <= child_start and child_end <= parent_end:
            evidence = ConfluenceEvidence(
                rule_name=self.name,
                evidence_code=EVIDENCE_TEMPORALLY_CONTAINED,
                message="Child wave is fully contained in parent wave",
                weight=config.evidence_weight_temporal,
                measured_value=(child_start, child_end),
                expected_value=(parent_start, parent_end),
            )
            return ConfluenceRuleResult(
                evidences=(evidence,),
                maximum_score=config.evidence_weight_temporal,
            )

        disjoint = child_end < parent_start or child_start > parent_end
        severity = ConfluenceSeverity.CRITICAL if disjoint else ConfluenceSeverity.WARNING
        conflict = ConfluenceConflict(
            rule_name=self.name,
            conflict_code=CONFLICT_TEMPORAL_CONTAINMENT_MISSING,
            message=(
                "Child wave lies outside the parent time range"
                if disjoint
                else "Child wave only partially overlaps the parent time range"
            ),
            severity=severity,
            measured_value=(child_start, child_end),
            expected_value=(parent_start, parent_end),
        )
        return ConfluenceRuleResult(
            conflicts=(conflict,),
            maximum_score=config.evidence_weight_temporal,
        )


@dataclass(frozen=True, slots=True)
class StructuralContinuityRule:
    """Check that the relation is structurally compatible with the evaluated nodes."""

    name: str = "structural_continuity_rule"

    def evaluate(
        self,
        relation: ParentChildRelation,
        parent_node: TrendNode | None,
        child_node: TrendNode | None,
        config: ConfluenceConfig,
    ) -> ConfluenceRuleResult:
        if parent_node is None or child_node is None:
            conflict = ConfluenceConflict(
                rule_name=self.name,
                conflict_code=CONFLICT_STRUCTURAL_RELATION_INVALID,
                message="Structural continuity cannot be evaluated without both nodes",
                severity=ConfluenceSeverity.CRITICAL,
                measured_value=None,
                expected_value="both nodes present",
            )
            return ConfluenceRuleResult(
                conflicts=(conflict,),
                maximum_score=config.evidence_weight_structure,
            )

        same_relation_nodes = (
            relation.parent_timeframe == parent_node.timeframe
            and relation.child_timeframe == child_node.timeframe
        )
        compatible_symbols = (
            parent_node.selected_wave_candidate.wave_candidate.wave.symbol
            == child_node.selected_wave_candidate.wave_candidate.wave.symbol
        )
        hierarchy_order_valid = relation.parent_timeframe < relation.child_timeframe
        no_self_relation = (
            relation.parent_timeframe != relation.child_timeframe and parent_node is not child_node
        )

        if (
            same_relation_nodes
            and compatible_symbols
            and hierarchy_order_valid
            and no_self_relation
        ):
            evidence = ConfluenceEvidence(
                rule_name=self.name,
                evidence_code=EVIDENCE_STRUCTURAL_RELATION_VALID,
                message="Relation is structurally compatible with the evaluated nodes",
                weight=config.evidence_weight_structure,
                measured_value=(
                    relation.parent_timeframe.value,
                    relation.child_timeframe.value,
                    parent_node.selected_wave_candidate.wave_candidate.wave.symbol.value,
                    child_node.selected_wave_candidate.wave_candidate.wave.symbol.value,
                ),
                expected_value=(
                    "matching relation nodes, compatible symbols, higher parent timeframe"
                ),
            )
            return ConfluenceRuleResult(
                evidences=(evidence,),
                maximum_score=config.evidence_weight_structure,
            )

        conflict = ConfluenceConflict(
            rule_name=self.name,
            conflict_code=CONFLICT_STRUCTURAL_RELATION_INVALID,
            message="Relation is not structurally compatible with the evaluated nodes",
            severity=ConfluenceSeverity.CRITICAL,
            measured_value={
                "relation_parent": relation.parent_timeframe.value,
                "relation_child": relation.child_timeframe.value,
                "node_parent": parent_node.timeframe.value,
                "node_child": child_node.timeframe.value,
                "parent_symbol": (
                    parent_node.selected_wave_candidate.wave_candidate.wave.symbol.value
                ),
                "child_symbol": child_node.selected_wave_candidate.wave_candidate.wave.symbol.value,
            },
            expected_value=("matching relation nodes, compatible symbols, higher parent timeframe"),
        )
        return ConfluenceRuleResult(
            conflicts=(conflict,),
            maximum_score=config.evidence_weight_structure,
        )


@dataclass(frozen=True, slots=True)
class ScoreSupportRule:
    """Check whether existing scores meet minimum confluence thresholds."""

    name: str = "score_support_rule"

    def evaluate(
        self,
        _relation: ParentChildRelation,
        parent_node: TrendNode | None,
        child_node: TrendNode | None,
        config: ConfluenceConfig,
    ) -> ConfluenceRuleResult:
        if parent_node is None or child_node is None:
            conflict = ConfluenceConflict(
                rule_name=self.name,
                conflict_code=CONFLICT_SCORE_THRESHOLD_NOT_REACHED,
                message="Score support cannot be evaluated without both nodes",
                severity=ConfluenceSeverity.CRITICAL,
                measured_value=None,
                expected_value="both nodes present",
            )
            return ConfluenceRuleResult(
                conflicts=(conflict,),
                maximum_score=config.evidence_weight_score,
            )

        parent_score = parent_node.selected_wave_candidate.wave_score.percentage
        child_score = child_node.selected_wave_candidate.wave_score.percentage

        if (
            parent_score >= config.minimum_parent_score_percent
            and child_score >= config.minimum_child_score_percent
        ):
            evidence = ConfluenceEvidence(
                rule_name=self.name,
                evidence_code=EVIDENCE_SCORE_THRESHOLDS_REACHED,
                message="Parent and child scores meet the configured thresholds",
                weight=config.evidence_weight_score,
                measured_value=(parent_score, child_score),
                expected_value=(
                    config.minimum_parent_score_percent,
                    config.minimum_child_score_percent,
                ),
            )
            return ConfluenceRuleResult(
                evidences=(evidence,),
                maximum_score=config.evidence_weight_score,
            )

        conflict = ConfluenceConflict(
            rule_name=self.name,
            conflict_code=CONFLICT_SCORE_THRESHOLD_NOT_REACHED,
            message="Parent or child score does not meet the configured thresholds",
            severity=ConfluenceSeverity.WARNING,
            measured_value=(parent_score, child_score),
            expected_value=(
                config.minimum_parent_score_percent,
                config.minimum_child_score_percent,
            ),
        )
        return ConfluenceRuleResult(
            conflicts=(conflict,),
            maximum_score=config.evidence_weight_score,
        )


@dataclass(frozen=True, slots=True)
class RelationConfluenceResult:
    """Confluence evaluation for one parent/child relation."""

    relation: ParentChildRelation
    parent_node: TrendNode | None
    child_node: TrendNode | None
    evidences: tuple[ConfluenceEvidence, ...]
    conflicts: tuple[ConfluenceConflict, ...]
    confluence_score: Decimal
    maximum_confluence_score: Decimal
    confluence_percent: Decimal
    maximum_confluence_percent: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        _validate_decimal_range(
            self.confluence_score,
            _ZERO,
            self.maximum_confluence_score,
            "confluence_score",
            allow_zero=True,
        )
        _validate_decimal_range(
            self.confluence_percent,
            _ZERO,
            self.maximum_confluence_percent,
            "confluence_percent",
            allow_zero=True,
        )
        _validate_decimal_range(
            self.maximum_confluence_score,
            _ZERO,
            None,
            "maximum_confluence_score",
            allow_zero=False,
        )
        _validate_decimal_range(
            self.maximum_confluence_percent,
            _ZERO,
            None,
            "maximum_confluence_percent",
            allow_zero=False,
        )
        _validate_unique_rule_codes(self.evidences, self.conflicts)

    @property
    def is_confluent(self) -> bool:
        """Return True when the relation has positive evidence and no critical conflict."""

        has_positive_evidence = any(evidence.weight > _ZERO for evidence in self.evidences)
        has_critical_conflict = any(
            conflict.severity is ConfluenceSeverity.CRITICAL for conflict in self.conflicts
        )
        return has_positive_evidence and not has_critical_conflict

    @property
    def has_conflicts(self) -> bool:
        """Return True when one or more conflicts were reported."""

        return bool(self.conflicts)

    @property
    def evidence_count(self) -> int:
        """Return the number of evidences."""

        return len(self.evidences)

    @property
    def conflict_count(self) -> int:
        """Return the number of conflicts."""

        return len(self.conflicts)

    @property
    def sort_key(self) -> tuple[int, int, str]:
        """Return a deterministic key used for stable ordering."""

        return (
            self.relation.parent_timeframe.hierarchy_index,
            self.relation.child_timeframe.hierarchy_index,
            self.relation.relation_type.value,
        )

    @classmethod
    def from_rule_results(
        cls,
        *,
        relation: ParentChildRelation,
        parent_node: TrendNode | None,
        child_node: TrendNode | None,
        rule_results: tuple[ConfluenceRuleResult, ...],
        maximum_confluence_percent: Decimal,
    ) -> RelationConfluenceResult:
        evidences = tuple(evidence for result in rule_results for evidence in result.evidences)
        conflicts = tuple(conflict for result in rule_results for conflict in result.conflicts)
        maximum_confluence_score = sum(
            (result.maximum_score for result in rule_results),
            _ZERO,
        )
        confluence_score = sum((evidence.weight for evidence in evidences), _ZERO)
        confluence_percent = _scale_percent(
            confluence_score=confluence_score,
            maximum_confluence_score=maximum_confluence_score,
            maximum_confluence_percent=maximum_confluence_percent,
        )
        return cls(
            relation=relation,
            parent_node=parent_node,
            child_node=child_node,
            evidences=evidences,
            conflicts=conflicts,
            confluence_score=confluence_score,
            maximum_confluence_score=maximum_confluence_score,
            confluence_percent=confluence_percent,
            maximum_confluence_percent=maximum_confluence_percent,
        )


@dataclass(frozen=True, slots=True)
class MultiTimeframeConfluenceResult:
    """Aggregated confluence analysis across all hierarchy relations."""

    relation_results: tuple[RelationConfluenceResult, ...] = ()
    analyzed_relations_count: int = 0
    confluence_score: Decimal = _ZERO
    maximum_confluence_score: Decimal = _ZERO
    confluence_percent: Decimal = _ZERO
    evidences: tuple[ConfluenceEvidence, ...] = ()
    conflicts: tuple[ConfluenceConflict, ...] = ()
    hierarchy_validation_result: HierarchyValidationResult | None = None
    maximum_confluence_percent: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        _validate_decimal_range(
            self.confluence_score,
            _ZERO,
            self.maximum_confluence_score if self.maximum_confluence_score > _ZERO else None,
            "confluence_score",
            allow_zero=True,
        )
        _validate_decimal_range(
            self.confluence_percent,
            _ZERO,
            self.maximum_confluence_percent,
            "confluence_percent",
        )
        _validate_decimal_range(
            self.maximum_confluence_score,
            _ZERO,
            None,
            "maximum_confluence_score",
            allow_zero=True,
        )
        _validate_decimal_range(
            self.maximum_confluence_percent,
            _ZERO,
            None,
            "maximum_confluence_percent",
            allow_zero=False,
        )

        sorted_results = tuple(sorted(self.relation_results, key=lambda result: result.sort_key))
        object.__setattr__(self, "relation_results", sorted_results)

        if self.analyzed_relations_count != len(sorted_results):
            message = "analyzed_relations_count must equal the number of relation_results"
            raise DomainError(message)

    @property
    def is_confluent(self) -> bool:
        """Return True when at least one relation is confluent and no critical conflicts exist."""

        return self.confluence_count > 0 and not any(
            conflict.severity is ConfluenceSeverity.CRITICAL for conflict in self.conflicts
        )

    @property
    def has_conflicts(self) -> bool:
        """Return True when aggregated conflicts exist."""

        return bool(self.conflicts)

    @property
    def strongest_relation(self) -> RelationConfluenceResult | None:
        """Return the strongest relation using stable hierarchy order on ties."""

        if not self.relation_results:
            return None
        return max(self.relation_results, key=_relation_confluence_sort_key)

    @property
    def weakest_relation(self) -> RelationConfluenceResult | None:
        """Return the weakest relation using stable hierarchy order on ties."""

        if not self.relation_results:
            return None
        return min(self.relation_results, key=_relation_confluence_sort_key)

    @property
    def confluence_count(self) -> int:
        """Return the number of confluent relations."""

        return sum(1 for result in self.relation_results if result.is_confluent)

    @property
    def conflict_count(self) -> int:
        """Return the number of aggregated conflicts."""

        return len(self.conflicts)

    @property
    def is_empty(self) -> bool:
        """Return True when no relations were analysed."""

        return not self.relation_results

    @classmethod
    def from_relation_results(
        cls,
        *,
        relation_results: tuple[RelationConfluenceResult, ...],
        hierarchy_validation_result: HierarchyValidationResult,
        maximum_confluence_percent: Decimal,
    ) -> MultiTimeframeConfluenceResult:
        evidences = tuple(evidence for result in relation_results for evidence in result.evidences)
        conflicts = tuple(conflict for result in relation_results for conflict in result.conflicts)
        if not hierarchy_validation_result.is_valid:
            conflicts = (
                *conflicts,
                ConfluenceConflict(
                    rule_name="hierarchy_validation_rule",
                    conflict_code=CONFLICT_HIERARCHY_INVALID,
                    message="Trend hierarchy failed structural validation",
                    severity=ConfluenceSeverity.CRITICAL,
                    measured_value=hierarchy_validation_result.issues,
                    expected_value="valid hierarchy",
                ),
            )

        maximum_confluence_score = sum(
            (result.maximum_confluence_score for result in relation_results),
            _ZERO,
        )
        confluence_score = sum((result.confluence_score for result in relation_results), _ZERO)
        confluence_percent = _scale_percent(
            confluence_score=confluence_score,
            maximum_confluence_score=maximum_confluence_score,
            maximum_confluence_percent=maximum_confluence_percent,
        )
        return cls(
            relation_results=relation_results,
            analyzed_relations_count=len(relation_results),
            confluence_score=confluence_score,
            maximum_confluence_score=maximum_confluence_score,
            confluence_percent=confluence_percent,
            evidences=evidences,
            conflicts=conflicts,
            hierarchy_validation_result=hierarchy_validation_result,
            maximum_confluence_percent=maximum_confluence_percent,
        )


def _default_confluence_rules() -> tuple[ConfluenceRule, ...]:
    """Return the built-in deterministic rule set in evaluation order."""

    return cast(
        "tuple[ConfluenceRule, ...]",
        (
            StructuralContinuityRule(),
            DirectionAlignmentRule(),
            TemporalContainmentRule(),
            ScoreSupportRule(),
        ),
    )


@dataclass(frozen=True, slots=True)
class MultiTimeframeConfluenceAnalyzer:
    """Deterministically evaluate confluence across a trend hierarchy."""

    config: ConfluenceConfig = field(default_factory=ConfluenceConfig)
    rules: tuple[ConfluenceRule, ...] = field(default_factory=_default_confluence_rules)

    def __post_init__(self) -> None:
        if not self.rules:
            message = "At least one confluence rule must be configured"
            raise DomainError(message)

    def analyze(self, hierarchy: TrendHierarchy) -> MultiTimeframeConfluenceResult:
        """Evaluate each hierarchy relation without changing the hierarchy or scores."""

        validation_result = hierarchy.validation
        node_by_timeframe = {node.timeframe: node for node in hierarchy.nodes}
        relation_results = tuple(
            self._analyze_relation(relation, node_by_timeframe) for relation in hierarchy.relations
        )
        return MultiTimeframeConfluenceResult.from_relation_results(
            relation_results=relation_results,
            hierarchy_validation_result=validation_result,
            maximum_confluence_percent=self.config.maximum_confluence_percent,
        )

    def _analyze_relation(
        self,
        relation: ParentChildRelation,
        node_by_timeframe: dict[Timeframe, TrendNode],
    ) -> RelationConfluenceResult:
        parent_node = node_by_timeframe.get(relation.parent_timeframe)
        child_node = node_by_timeframe.get(relation.child_timeframe)
        rule_results = tuple(
            rule.evaluate(relation, parent_node, child_node, self.config) for rule in self.rules
        )
        return RelationConfluenceResult.from_rule_results(
            relation=relation,
            parent_node=parent_node,
            child_node=child_node,
            rule_results=rule_results,
            maximum_confluence_percent=self.config.maximum_confluence_percent,
        )


def _scale_percent(
    *,
    confluence_score: Decimal,
    maximum_confluence_score: Decimal,
    maximum_confluence_percent: Decimal,
) -> Decimal:
    if maximum_confluence_score == _ZERO:
        return _ZERO
    return (confluence_score / maximum_confluence_score) * maximum_confluence_percent


def _validate_decimal_range(
    value: Decimal,
    minimum: Decimal,
    maximum: Decimal | None,
    field_name: str,
    *,
    allow_zero: bool = True,
) -> None:
    if not value.is_finite():
        message = f"{field_name} must be finite"
        raise DomainError(message)

    if allow_zero:
        if value < minimum:
            message = f"{field_name} must be >= {minimum}"
            raise DomainError(message)
    elif value <= minimum:
        message = f"{field_name} must be > {minimum}"
        raise DomainError(message)

    if maximum is not None and value > maximum:
        message = f"{field_name} must be <= {maximum}"
        raise DomainError(message)


def _validate_unique_rule_codes(
    evidences: tuple[ConfluenceEvidence, ...],
    conflicts: tuple[ConfluenceConflict, ...],
) -> None:
    seen: set[tuple[str, str]] = set()

    for evidence in evidences:
        key = (evidence.rule_name, evidence.evidence_code)
        if key in seen:
            message = "Duplicate evidence codes for a rule are not allowed"
            raise DomainError(message)
        seen.add(key)

    for conflict in conflicts:
        key = (conflict.rule_name, conflict.conflict_code)
        if key in seen:
            message = "Duplicate conflict codes for a rule are not allowed"
            raise DomainError(message)
        seen.add(key)


def _relation_confluence_sort_key(result: RelationConfluenceResult) -> tuple[Decimal, Decimal]:
    """Return a stable score key for selecting strongest or weakest relations."""

    return (result.confluence_percent, result.confluence_score)
