"""Interfaces and protocols for FazzTV components."""

from .providers import (
    ProviderProtocol,
    ConfigurationProtocol,
    ValidationProtocol,
    CacheableProtocol,
    LoggableProtocol
)
from .media import (
    MediaProcessorProtocol,
    BroadcasterProtocol,
    SerializerProtocol
)
from .api import (
    APIClientProtocol,
    SearchClientProtocol,
    ContentClientProtocol
)

__all__ = [
    # Provider interfaces
    "ProviderProtocol",
    "ConfigurationProtocol",
    "ValidationProtocol",
    "CacheableProtocol",
    "LoggableProtocol",
    # Media interfaces
    "MediaProcessorProtocol",
    "BroadcasterProtocol",
    "SerializerProtocol",
    # API interfaces
    "APIClientProtocol",
    "SearchClientProtocol",
    "ContentClientProtocol"
]