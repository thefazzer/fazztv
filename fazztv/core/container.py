"""Dependency injection container for FazzTV."""

import inspect
from typing import Any, Dict, Type, TypeVar, Callable, Optional, Set, List
from dataclasses import dataclass
from enum import Enum
from loguru import logger

T = TypeVar('T')


class ServiceScope(Enum):
    """Service lifecycle scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceRegistration:
    """Registration information for a service."""
    service_type: Type
    implementation: Type
    factory: Optional[Callable[..., Any]]
    scope: ServiceScope
    dependencies: List[Type]
    metadata: Dict[str, Any]


class ServiceRegistry:
    """Registry for managing service registrations."""

    def __init__(self):
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._instances: Dict[Type, Any] = {}
        self._building: Set[Type] = set()

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[..., T]] = None,
        **metadata: Any
    ) -> None:
        """Register a singleton service."""
        self._register(service_type, implementation, factory, ServiceScope.SINGLETON, metadata)

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[..., T]] = None,
        **metadata: Any
    ) -> None:
        """Register a transient service."""
        self._register(service_type, implementation, factory, ServiceScope.TRANSIENT, metadata)

    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[..., T]] = None,
        **metadata: Any
    ) -> None:
        """Register a scoped service."""
        self._register(service_type, implementation, factory, ServiceScope.SCOPED, metadata)

    def _register(
        self,
        service_type: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        scope: ServiceScope = ServiceScope.SINGLETON,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Internal registration method."""
        if implementation is None and factory is None:
            implementation = service_type

        if implementation and factory:
            raise ValueError("Cannot specify both implementation and factory")

        if implementation:
            dependencies = self._extract_dependencies(implementation)
        else:
            dependencies = self._extract_dependencies(factory)

        registration = ServiceRegistration(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            scope=scope,
            dependencies=dependencies,
            metadata=metadata or {}
        )

        self._registrations[service_type] = registration
        logger.debug(f"Registered {service_type.__name__} with scope {scope.value}")

    def _extract_dependencies(self, target: Type) -> List[Type]:
        """Extract dependencies from constructor or factory signature."""
        try:
            if target is None:
                return []

            if inspect.isclass(target):
                sig = inspect.signature(target.__init__)
            else:
                sig = inspect.signature(target)

            dependencies = []
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                if param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)

            return dependencies
        except Exception as e:
            logger.warning(f"Failed to extract dependencies from {target}: {e}")
            return []

    def get_registration(self, service_type: Type) -> Optional[ServiceRegistration]:
        """Get registration for a service type."""
        return self._registrations.get(service_type)

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._registrations

    def get_all_registrations(self) -> Dict[Type, ServiceRegistration]:
        """Get all registrations."""
        return self._registrations.copy()


class DIContainer:
    """Dependency injection container."""

    def __init__(self, registry: Optional[ServiceRegistry] = None):
        self.registry = registry or ServiceRegistry()
        self._scoped_instances: Dict[Type, Any] = {}

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance."""
        return self._resolve_internal(service_type)

    def _resolve_internal(self, service_type: Type) -> Any:
        """Internal resolution method with circular dependency detection."""
        if service_type in self.registry._building:
            raise RuntimeError(f"Circular dependency detected for {service_type.__name__}")

        registration = self.registry.get_registration(service_type)
        if not registration:
            raise ValueError(f"Service {service_type.__name__} is not registered")

        # Handle singleton scope
        if registration.scope == ServiceScope.SINGLETON:
            if service_type in self.registry._instances:
                return self.registry._instances[service_type]

        # Handle scoped scope
        elif registration.scope == ServiceScope.SCOPED:
            if service_type in self._scoped_instances:
                return self._scoped_instances[service_type]

        # Build the service
        self.registry._building.add(service_type)
        try:
            instance = self._build_instance(registration)

            # Store based on scope
            if registration.scope == ServiceScope.SINGLETON:
                self.registry._instances[service_type] = instance
            elif registration.scope == ServiceScope.SCOPED:
                self._scoped_instances[service_type] = instance

            logger.debug(f"Created instance of {service_type.__name__}")
            return instance

        finally:
            self.registry._building.discard(service_type)

    def _build_instance(self, registration: ServiceRegistration) -> Any:
        """Build an instance from registration."""
        # Resolve dependencies
        dependencies = {}
        for dep_type in registration.dependencies:
            dependencies[self._get_param_name(dep_type)] = self._resolve_internal(dep_type)

        # Create instance
        if registration.factory:
            return registration.factory(**dependencies)
        else:
            return registration.implementation(**dependencies)

    def _get_param_name(self, dep_type: Type) -> str:
        """Get parameter name for a dependency type."""
        # This is a simple heuristic - could be improved
        return dep_type.__name__.lower().replace('protocol', '').replace('interface', '')

    def clear_scoped(self) -> None:
        """Clear scoped instances."""
        self._scoped_instances.clear()
        logger.debug("Cleared scoped instances")

    def get_service_info(self, service_type: Type) -> Dict[str, Any]:
        """Get information about a registered service."""
        registration = self.registry.get_registration(service_type)
        if not registration:
            return {}

        return {
            "service_type": service_type.__name__,
            "implementation": registration.implementation.__name__ if registration.implementation else "factory",
            "scope": registration.scope.value,
            "dependencies": [dep.__name__ for dep in registration.dependencies],
            "metadata": registration.metadata,
            "instance_created": service_type in self.registry._instances or service_type in self._scoped_instances
        }

    def validate_registrations(self) -> List[str]:
        """Validate all registrations for potential issues."""
        errors = []

        for service_type, registration in self.registry.get_all_registrations().items():
            # Check for missing dependencies
            for dep_type in registration.dependencies:
                if not self.registry.is_registered(dep_type):
                    errors.append(f"Service {service_type.__name__} depends on unregistered service {dep_type.__name__}")

        # Check for circular dependencies (basic check)
        try:
            for service_type in self.registry.get_all_registrations():
                self._check_circular_dependencies(service_type, set())
        except RuntimeError as e:
            errors.append(str(e))

        return errors

    def _check_circular_dependencies(self, service_type: Type, visited: Set[Type]) -> None:
        """Check for circular dependencies recursively."""
        if service_type in visited:
            raise RuntimeError(f"Circular dependency detected involving {service_type.__name__}")

        registration = self.registry.get_registration(service_type)
        if not registration:
            return

        visited.add(service_type)
        for dep_type in registration.dependencies:
            self._check_circular_dependencies(dep_type, visited.copy())

    def register_singleton(self, service_type: Type[T], implementation: Optional[Type[T]] = None, factory: Optional[Callable[..., T]] = None, **metadata: Any) -> None:
        """Register a singleton service."""
        self.registry.register_singleton(service_type, implementation, factory, **metadata)

    def register_transient(self, service_type: Type[T], implementation: Optional[Type[T]] = None, factory: Optional[Callable[..., T]] = None, **metadata: Any) -> None:
        """Register a transient service."""
        self.registry.register_transient(service_type, implementation, factory, **metadata)

    def register_scoped(self, service_type: Type[T], implementation: Optional[Type[T]] = None, factory: Optional[Callable[..., T]] = None, **metadata: Any) -> None:
        """Register a scoped service."""
        self.registry.register_scoped(service_type, implementation, factory, **metadata)