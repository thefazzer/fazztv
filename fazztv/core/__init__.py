"""Core FazzTV components including dependency injection."""

from .container import DIContainer, ServiceRegistry
from .factory import ComponentFactory
from .lifecycle import ServiceLifecycle, LifecycleManager

__all__ = [
    "DIContainer",
    "ServiceRegistry",
    "ComponentFactory",
    "ServiceLifecycle",
    "LifecycleManager"
]