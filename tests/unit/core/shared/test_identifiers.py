from uuid import UUID

import pytest

from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId


def test_new_entity_id_is_not_nil() -> None:
    assert EntityId.new().value.int != 0


def test_parse_entity_id() -> None:
    raw = "7abf4cb4-a834-49ec-b6bb-66fd69d73c93"
    entity_id = EntityId.parse(raw)
    assert entity_id.value == UUID(raw)
    assert str(entity_id) == raw


def test_parse_rejects_invalid_value() -> None:
    with pytest.raises(DomainError, match="Invalid entity identifier"):
        EntityId.parse("not-a-uuid")


def test_nil_uuid_is_rejected() -> None:
    with pytest.raises(DomainError, match="nil UUID"):
        EntityId(UUID(int=0))
