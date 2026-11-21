from datetime import UTC

from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.infrastructure.analysis import SystemAnalysisClock, UuidAnalysisIdProvider


def test_system_analysis_clock_returns_utc_datetime() -> None:
    now = SystemAnalysisClock().now()

    assert now.tzinfo is UTC


def test_uuid_analysis_id_provider_returns_non_nil_entity_id() -> None:
    provider = UuidAnalysisIdProvider()

    first = provider.next_analysis_id()
    second = provider.next_analysis_id()

    assert isinstance(first, EntityId)
    assert isinstance(second, EntityId)
    assert first != second
