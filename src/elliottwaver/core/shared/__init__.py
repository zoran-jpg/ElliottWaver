"""Shared foundation primitives."""

from elliottwaver.core.shared.entity import Entity
from elliottwaver.core.shared.errors import DomainError
from elliottwaver.core.shared.identifiers import EntityId
from elliottwaver.core.shared.value_object import ValueObject

__all__ = ["DomainError", "Entity", "EntityId", "ValueObject"]
