"""Shared exception hierarchy."""


class ElliottWaverError(Exception):
    """Base exception for expected ElliottWaver errors."""


class DomainError(ElliottWaverError):
    """Raised when a domain invariant is violated."""


class ConfigurationError(ElliottWaverError):
    """Raised when application configuration is invalid."""
