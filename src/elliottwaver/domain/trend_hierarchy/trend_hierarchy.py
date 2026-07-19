"""Trend hierarchy domain models and deterministic hierarchy builder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.domain.multi_timeframe import MultiTimeframeAnalysis, Timeframe
    from elliottwaver.domain.selection import SelectedWaveCandidate


class RelationType(StrEnum):
    """Structural relationship type between two timeframe nodes."""

    PARENT = "parent"
    CHILD = "child"


@dataclass(frozen=True, slots=True)
class ParentChildRelation:
    """A structural relationship between parent and child timeframes."""

    parent_timeframe: Timeframe
    child_timeframe: Timeframe
    relation_type: RelationType
    rationale: str

    def __post_init__(self) -> None:
        if self.parent_timeframe == self.child_timeframe:
            message = "parent_timeframe and child_timeframe must differ"
            raise DomainError(message)

        if not self.rationale.strip():
            message = "rationale must not be empty"
            raise DomainError(message)


@dataclass(frozen=True, slots=True)
class TrendNode:
    """A selected wave candidate bound to one hierarchy timeframe level."""

    timeframe: Timeframe
    selected_wave_candidate: SelectedWaveCandidate
    parent_timeframe: Timeframe | None
    child_timeframes: tuple[Timeframe, ...]
    depth: int
    analysed_at: datetime

    def __post_init__(self) -> None:
        if self.analysed_at.tzinfo is None or self.analysed_at.utcoffset() != UTC.utcoffset(None):
            message = "analysed_at must be timezone-aware UTC"
            raise DomainError(message)

        if self.depth < 0:
            message = "depth must be >= 0"
            raise DomainError(message)

        if self.parent_timeframe is None and self.depth != 0:
            message = "root nodes must have depth 0"
            raise DomainError(message)

        if self.parent_timeframe is not None and self.depth == 0:
            message = "non-root nodes must have depth > 0"
            raise DomainError(message)

        if self.parent_timeframe == self.timeframe:
            message = "node parent_timeframe must not equal node timeframe"
            raise DomainError(message)

        if self.timeframe in self.child_timeframes:
            message = "node child_timeframes must not contain node timeframe"
            raise DomainError(message)

        if len(set(self.child_timeframes)) != len(self.child_timeframes):
            message = "node child_timeframes must be unique"
            raise DomainError(message)

    @property
    def is_root(self) -> bool:
        """Return True when the node has no parent."""

        return self.parent_timeframe is None

    @property
    def is_leaf(self) -> bool:
        """Return True when the node has no children."""

        return not self.child_timeframes


@dataclass(frozen=True, slots=True)
class HierarchyValidationResult:
    """Validation result for structural hierarchy invariants."""

    is_valid: bool
    root_count: int
    has_cycle: bool
    has_duplicate_timeframes: bool
    has_missing_parent: bool
    has_consistency_errors: bool
    issues: tuple[str, ...] = ()

    @classmethod
    def evaluate(cls, hierarchy: TrendHierarchy) -> HierarchyValidationResult:
        """Validate hierarchy structure without raising exceptions."""

        node_by_timeframe: dict[Timeframe, TrendNode] = {}
        duplicate_timeframes = False

        for node in hierarchy.nodes:
            if node.timeframe in node_by_timeframe:
                duplicate_timeframes = True
                continue
            node_by_timeframe[node.timeframe] = node

        root_count = sum(1 for node in hierarchy.nodes if node.parent_timeframe is None)
        missing_parent = any(
            node.parent_timeframe is not None and node.parent_timeframe not in node_by_timeframe
            for node in hierarchy.nodes
        )

        consistency_errors = False

        for node in hierarchy.nodes:
            if node.parent_timeframe is not None:
                parent = node_by_timeframe.get(node.parent_timeframe)
                if parent is None or node.timeframe not in parent.child_timeframes:
                    consistency_errors = True

            for child_timeframe in node.child_timeframes:
                child = node_by_timeframe.get(child_timeframe)
                if child is None or child.parent_timeframe != node.timeframe:
                    consistency_errors = True

        has_cycle = _contains_cycle(node_by_timeframe)
        root_required_ok = root_count == 1 if hierarchy.nodes else True

        issues: list[str] = []
        if not root_required_ok:
            issues.append("Hierarchy must contain exactly one root node")
        if has_cycle:
            issues.append("Hierarchy must not contain cycles")
        if duplicate_timeframes:
            issues.append("Hierarchy must not contain duplicate timeframes")
        if missing_parent:
            issues.append("Hierarchy contains node(s) with missing parent")
        if consistency_errors:
            issues.append("Hierarchy contains inconsistent parent/child references")

        is_valid = not issues

        return cls(
            is_valid=is_valid,
            root_count=root_count,
            has_cycle=has_cycle,
            has_duplicate_timeframes=duplicate_timeframes,
            has_missing_parent=missing_parent,
            has_consistency_errors=consistency_errors,
            issues=tuple(issues),
        )


@dataclass(frozen=True, slots=True)
class TrendHierarchy:
    """Immutable hierarchy of selected wave candidates across timeframes."""

    nodes: tuple[TrendNode, ...] = ()
    relations: tuple[ParentChildRelation, ...] = ()

    def __post_init__(self) -> None:
        sorted_nodes = tuple(sorted(self.nodes, key=lambda node: node.timeframe.hierarchy_index))
        sorted_relations = tuple(
            sorted(
                self.relations,
                key=lambda relation: (
                    relation.parent_timeframe.hierarchy_index,
                    relation.child_timeframe.hierarchy_index,
                    relation.relation_type.value,
                ),
            )
        )

        object.__setattr__(self, "nodes", sorted_nodes)
        object.__setattr__(self, "relations", sorted_relations)

    @property
    def root(self) -> TrendNode | None:
        """Return the unique root node when present and unambiguous."""

        root_nodes = tuple(node for node in self.nodes if node.parent_timeframe is None)
        if len(root_nodes) != 1:
            return None
        return root_nodes[0]

    @property
    def leaf_nodes(self) -> tuple[TrendNode, ...]:
        """Return all leaf nodes in stable timeframe order."""

        return tuple(node for node in self.nodes if node.is_leaf)

    @property
    def depth(self) -> int:
        """Return the maximum hierarchy depth."""

        return max((node.depth for node in self.nodes), default=0)

    @property
    def node_count(self) -> int:
        """Return total number of hierarchy nodes."""

        return len(self.nodes)

    @property
    def has_root(self) -> bool:
        """Return True when exactly one root node exists."""

        return self.root is not None

    @property
    def validation(self) -> HierarchyValidationResult:
        """Return structural validation result."""

        return HierarchyValidationResult.evaluate(self)

    @property
    def is_valid(self) -> bool:
        """Return True when validation passes."""

        return self.validation.is_valid


@dataclass(frozen=True, slots=True)
class TrendHierarchyBuilder:
    """Deterministically build hierarchy from multi-timeframe selections."""

    def build(self, analysis: MultiTimeframeAnalysis) -> TrendHierarchy:
        """Build hierarchy using only ordered timeframe relationships."""

        selected_analyses = tuple(
            timeframe_analysis
            for timeframe_analysis in analysis.analyses
            if timeframe_analysis.primary_candidate is not None
        )

        if not selected_analyses:
            return TrendHierarchy()

        nodes: list[TrendNode] = []
        relations: list[ParentChildRelation] = []

        for index, timeframe_analysis in enumerate(selected_analyses):
            parent_timeframe = selected_analyses[index - 1].timeframe if index > 0 else None
            child_timeframes = (
                (selected_analyses[index + 1].timeframe,)
                if index + 1 < len(selected_analyses)
                else ()
            )

            primary_candidate = timeframe_analysis.primary_candidate
            if primary_candidate is None:
                continue

            nodes.append(
                TrendNode(
                    timeframe=timeframe_analysis.timeframe,
                    selected_wave_candidate=primary_candidate,
                    parent_timeframe=parent_timeframe,
                    child_timeframes=child_timeframes,
                    depth=index,
                    analysed_at=timeframe_analysis.analysed_at,
                )
            )

            if index + 1 < len(selected_analyses):
                parent = timeframe_analysis.timeframe
                child = selected_analyses[index + 1].timeframe
                relations.append(
                    ParentChildRelation(
                        parent_timeframe=parent,
                        child_timeframe=child,
                        relation_type=RelationType.PARENT,
                        rationale="Derived from timeframe hierarchy order",
                    )
                )
                relations.append(
                    ParentChildRelation(
                        parent_timeframe=parent,
                        child_timeframe=child,
                        relation_type=RelationType.CHILD,
                        rationale="Derived from timeframe hierarchy order",
                    )
                )

        return TrendHierarchy(nodes=tuple(nodes), relations=tuple(relations))


def _contains_cycle(node_by_timeframe: dict[Timeframe, TrendNode]) -> bool:
    """Return True if hierarchy nodes contain a child-cycle."""

    visited: set[Timeframe] = set()
    recursion_stack: set[Timeframe] = set()

    def visit(timeframe: Timeframe) -> bool:
        if timeframe in recursion_stack:
            return True
        if timeframe in visited:
            return False

        visited.add(timeframe)
        recursion_stack.add(timeframe)

        node = node_by_timeframe.get(timeframe)
        if node is None:
            recursion_stack.remove(timeframe)
            return False

        for child_timeframe in node.child_timeframes:
            if child_timeframe in node_by_timeframe and visit(child_timeframe):
                recursion_stack.remove(timeframe)
                return True

        recursion_stack.remove(timeframe)
        return False

    return any(visit(timeframe) for timeframe in node_by_timeframe)
