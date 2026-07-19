from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from tests.unit.domain.context.helpers import (
    make_confluence_result,
    make_selected_wave_candidate,
    make_trend_hierarchy,
)

from elliottwaver.application import (
    ContextRequest,
    ContextResponse,
    ContextService,
)
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId

_CREATED_AT = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
_CONTEXT_ID = EntityId.parse("12345678-1234-5678-1234-567812349999")


class StaticClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class StaticIdProvider:
    def __init__(self, value: EntityId) -> None:
        self.value = value

    def next_context_id(self) -> EntityId:
        return self.value


def test_context_service_creates_context_response() -> None:
    service = ContextService(
        context_clock=StaticClock(_CREATED_AT),
        context_id_provider=StaticIdProvider(_CONTEXT_ID),
    )
    request = ContextRequest(
        selected_wave=make_selected_wave_candidate(score_percent="91"),
        trend_hierarchy=make_trend_hierarchy(root_direction="up", child_direction="up"),
        confluence_result=make_confluence_result(confluence_percent="84"),
        correlation_id="  corr-context-1  ",
    )

    response = service.create_context(request)

    assert isinstance(response, ContextResponse)
    assert response.metadata.context_id == _CONTEXT_ID
    assert response.metadata.created_at == _CREATED_AT
    assert response.metadata.correlation_id == "corr-context-1"
    assert response.context.selected_wave == request.selected_wave

    with pytest.raises(FrozenInstanceError):
        response.__setattr__("metadata", response.metadata)


def test_context_service_is_deterministic_for_same_inputs() -> None:
    service = ContextService(
        context_clock=StaticClock(_CREATED_AT),
        context_id_provider=StaticIdProvider(_CONTEXT_ID),
    )
    request = ContextRequest(
        selected_wave=make_selected_wave_candidate(score_percent="88"),
        trend_hierarchy=make_trend_hierarchy(root_direction="up", child_direction="up"),
        confluence_result=make_confluence_result(confluence_percent="70"),
    )

    first = service.create_context(request)
    second = service.create_context(request)

    assert first == second


def test_context_request_rejects_missing_selected_wave() -> None:
    with pytest.raises(DomainError, match="selected_wave must not be None"):
        ContextRequest(selected_wave=None)  # type: ignore[arg-type]


def test_context_service_rejects_naive_metadata_timestamp() -> None:
    service = ContextService(
        context_clock=StaticClock(datetime(2026, 7, 20, 10, 0)),  # noqa: DTZ001
        context_id_provider=StaticIdProvider(_CONTEXT_ID),
    )
    request = ContextRequest(selected_wave=make_selected_wave_candidate())

    with pytest.raises(DomainError, match="timezone-aware UTC"):
        service.create_context(request)
