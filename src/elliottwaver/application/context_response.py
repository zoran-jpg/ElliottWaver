"""Context use-case response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from elliottwaver.core.shared.errors import DomainError

if TYPE_CHECKING:
    from elliottwaver.core.shared.identifiers import EntityId
    from elliottwaver.domain.context import ElliottContext

_UTC_OFFSET = UTC.utcoffset(None)


@dataclass(frozen=True, slots=True)
class ContextMetadata:
    """Thin metadata envelope for context responses."""

    context_id: EntityId
    created_at: datetime
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() != _UTC_OFFSET:
            message = "created_at must be timezone-aware UTC"
            raise DomainError(message)

        normalized_correlation_id = self.correlation_id
        if normalized_correlation_id is not None:
            normalized_correlation_id = normalized_correlation_id.strip()
            if not normalized_correlation_id:
                message = "correlation_id must not be empty"
                raise DomainError(message)
            object.__setattr__(self, "correlation_id", normalized_correlation_id)


@dataclass(frozen=True, slots=True)
class ContextResponse:
    """Result contract for context creation."""

    context: ElliottContext
    metadata: ContextMetadata
