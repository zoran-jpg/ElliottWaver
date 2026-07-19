from dataclasses import dataclass

from elliottwaver.core.shared.entity import Entity
from elliottwaver.core.shared.identifiers import EntityId


@dataclass(eq=False, slots=True)
class ExampleEntity(Entity[EntityId]):
    name: str


@dataclass(eq=False, slots=True)
class OtherEntity(Entity[EntityId]):
    name: str


def test_entities_with_same_type_and_id_are_equal() -> None:
    entity_id = EntityId.new()
    first = ExampleEntity(id=entity_id, name="first")
    second = ExampleEntity(id=entity_id, name="second")
    assert first == second
    assert hash(first) == hash(second)


def test_entities_with_different_ids_are_not_equal() -> None:
    assert ExampleEntity(EntityId.new(), "same") != ExampleEntity(EntityId.new(), "same")


def test_entities_of_different_types_are_not_equal() -> None:
    entity_id = EntityId.new()
    assert ExampleEntity(entity_id, "same") != OtherEntity(entity_id, "same")
