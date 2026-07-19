"""Context use-case orchestration service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from elliottwaver.application.context_response import ContextMetadata, ContextResponse
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.domain.context import ContextBuilder

if TYPE_CHECKING:
    from datetime import datetime

    from elliottwaver.application.context_request import ContextRequest
    from elliottwaver.core.shared.identifiers import EntityId


@runtime_checkable
class ContextClock(Protocol):
    """Clock port for deterministic context timestamps."""

    def now(self) -> datetime:
        """Return timezone-aware UTC now."""


@runtime_checkable
class ContextIdProvider(Protocol):
    """Identifier port for context metadata."""

    def next_context_id(self) -> EntityId:
        """Return next context identifier."""


@dataclass(frozen=True, slots=True)
class ContextService:
    """Application service that creates structured Elliott context."""

    context_clock: ContextClock
    context_id_provider: ContextIdProvider
    context_builder: ContextBuilder = field(default_factory=ContextBuilder)

    def create_context(self, request: ContextRequest) -> ContextResponse:
        """Create deterministic context from existing analysis results."""

        selected_wave = request.selected_wave
        if selected_wave is None:
            message = "selected_wave must not be None"
            raise DomainError(message)

        context = self.context_builder.build(
            selected_wave=selected_wave,
            trend_hierarchy=request.trend_hierarchy,
            confluence_result=request.confluence_result,
            trend_level=request.trend_level,
        )

        metadata = ContextMetadata(
            context_id=self.context_id_provider.next_context_id(),
            created_at=self.context_clock.now(),
            correlation_id=request.correlation_id,
        )
        return ContextResponse(context=context, metadata=metadata)
