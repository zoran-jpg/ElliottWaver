"""Base entity abstraction."""

from dataclasses import dataclass

from elliottwaver.core.shared.identifiers import EntityId


@dataclass(eq=False, slots=True)
class Entity[EntityIdT: EntityId]:
    """Identity-based domain object."""

    id: EntityIdT

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))
