"""Service lifecycle management for FazzTV."""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger

from fazztv.core.logging import get_logger, ComponentLogger


class ServiceState(Enum):
    """Service lifecycle states."""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    FAILED = "failed"


class ServicePriority(Enum):
    """Service priority levels for startup/shutdown ordering."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class ServiceInfo:
    """Information about a managed service."""
    name: str
    instance: Any
    state: ServiceState
    priority: ServicePriority
    dependencies: Set[str]
    health_check: Optional[Callable[[], bool]]
    startup_timeout: float
    shutdown_timeout: float
    error_count: int = 0
    last_error: Optional[Exception] = None


class ServiceLifecycle(ABC):
    """Interface for services that need lifecycle management."""

    @abstractmethod
    async def startup(self) -> None:
        """Start the service."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Stop the service."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is healthy."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get service status information."""
        pass


class LifecycleManager:
    """Manages the lifecycle of multiple services."""

    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.logger = get_logger("LifecycleManager")
        self._shutdown_event = threading.Event()
        self._health_check_interval = 30.0  # seconds
        self._health_check_task: Optional[asyncio.Task] = None

    def register_service(
        self,
        name: str,
        instance: Any,
        priority: ServicePriority = ServicePriority.NORMAL,
        dependencies: Optional[Set[str]] = None,
        health_check: Optional[Callable[[], bool]] = None,
        startup_timeout: float = 30.0,
        shutdown_timeout: float = 10.0
    ) -> None:
        """Register a service for lifecycle management."""
        if name in self.services:
            raise ValueError(f"Service '{name}' is already registered")

        # Use instance's health_check method if available and none provided
        if health_check is None and hasattr(instance, 'health_check'):
            health_check = instance.health_check

        service_info = ServiceInfo(
            name=name,
            instance=instance,
            state=ServiceState.CREATED,
            priority=priority,
            dependencies=dependencies or set(),
            health_check=health_check,
            startup_timeout=startup_timeout,
            shutdown_timeout=shutdown_timeout
        )

        self.services[name] = service_info
        self.logger.info(f"Registered service: {name}", service=name, priority=priority.name)

    def unregister_service(self, name: str) -> None:
        """Unregister a service."""
        if name in self.services:
            service = self.services[name]
            if service.state == ServiceState.RUNNING:
                self.logger.warning(f"Unregistering running service: {name}")
            del self.services[name]
            self.logger.info(f"Unregistered service: {name}", service=name)

    async def start_all(self) -> None:
        """Start all registered services in dependency order."""
        self.logger.info("Starting all services")

        # Sort services by priority and resolve dependencies
        startup_order = self._resolve_startup_order()

        for service_name in startup_order:
            await self._start_service(service_name)

        # Start health monitoring
        await self._start_health_monitoring()

        self.logger.info("All services started successfully")

    async def stop_all(self) -> None:
        """Stop all services in reverse dependency order."""
        self.logger.info("Stopping all services")

        # Stop health monitoring
        await self._stop_health_monitoring()

        # Get shutdown order (reverse of startup)
        startup_order = self._resolve_startup_order()
        shutdown_order = list(reversed(startup_order))

        for service_name in shutdown_order:
            await self._stop_service(service_name)

        self.logger.info("All services stopped")

    async def restart_service(self, name: str) -> None:
        """Restart a specific service."""
        self.logger.info(f"Restarting service: {name}", service=name)

        if name not in self.services:
            raise ValueError(f"Service '{name}' is not registered")

        await self._stop_service(name)
        await self._start_service(name)

        self.logger.info(f"Service restarted: {name}", service=name)

    async def _start_service(self, name: str) -> None:
        """Start a single service."""
        service = self.services[name]

        if service.state == ServiceState.RUNNING:
            self.logger.debug(f"Service already running: {name}", service=name)
            return

        self.logger.info(f"Starting service: {name}", service=name)
        service.state = ServiceState.INITIALIZING

        try:
            # Check dependencies are running
            for dep_name in service.dependencies:
                if dep_name not in self.services:
                    raise RuntimeError(f"Dependency '{dep_name}' not registered")
                if self.services[dep_name].state != ServiceState.RUNNING:
                    raise RuntimeError(f"Dependency '{dep_name}' is not running")

            # Start the service
            if hasattr(service.instance, 'startup'):
                await asyncio.wait_for(
                    service.instance.startup(),
                    timeout=service.startup_timeout
                )
            elif hasattr(service.instance, 'start'):
                # Support both async and sync start methods
                start_method = service.instance.start
                if asyncio.iscoroutinefunction(start_method):
                    await asyncio.wait_for(start_method(), timeout=service.startup_timeout)
                else:
                    start_method()

            service.state = ServiceState.RUNNING
            self.logger.success(f"Service started: {name}", service=name)

        except asyncio.TimeoutError:
            service.state = ServiceState.ERROR
            service.error_count += 1
            error_msg = f"Service startup timeout: {name}"
            self.logger.error(error_msg, service=name, timeout=service.startup_timeout)
            raise RuntimeError(error_msg)

        except Exception as e:
            service.state = ServiceState.FAILED
            service.error_count += 1
            service.last_error = e
            self.logger.error(f"Service startup failed: {name} - {e}", service=name, error=str(e))
            raise

    async def _stop_service(self, name: str) -> None:
        """Stop a single service."""
        service = self.services[name]

        if service.state in [ServiceState.STOPPED, ServiceState.STOPPING]:
            return

        self.logger.info(f"Stopping service: {name}", service=name)
        service.state = ServiceState.STOPPING

        try:
            if hasattr(service.instance, 'shutdown'):
                await asyncio.wait_for(
                    service.instance.shutdown(),
                    timeout=service.shutdown_timeout
                )
            elif hasattr(service.instance, 'stop'):
                # Support both async and sync stop methods
                stop_method = service.instance.stop
                if asyncio.iscoroutinefunction(stop_method):
                    await asyncio.wait_for(stop_method(), timeout=service.shutdown_timeout)
                else:
                    stop_method()

            service.state = ServiceState.STOPPED
            self.logger.success(f"Service stopped: {name}", service=name)

        except asyncio.TimeoutError:
            service.state = ServiceState.ERROR
            error_msg = f"Service shutdown timeout: {name}"
            self.logger.error(error_msg, service=name, timeout=service.shutdown_timeout)
            # Force stop if possible
            if hasattr(service.instance, 'force_stop'):
                service.instance.force_stop()

        except Exception as e:
            service.state = ServiceState.ERROR
            service.last_error = e
            self.logger.error(f"Service shutdown failed: {name} - {e}", service=name, error=str(e))

    def _resolve_startup_order(self) -> List[str]:
        """Resolve service startup order based on dependencies and priorities."""
        # Simple topological sort with priority consideration
        remaining = set(self.services.keys())
        ordered = []

        while remaining:
            # Find services with no unresolved dependencies
            ready = []
            for service_name in remaining:
                service = self.services[service_name]
                if service.dependencies.issubset(set(ordered)):
                    ready.append(service_name)

            if not ready:
                # Circular dependency or missing dependency
                missing_deps = []
                for service_name in remaining:
                    service = self.services[service_name]
                    unresolved = service.dependencies - set(ordered)
                    if unresolved:
                        missing_deps.append(f"{service_name}: {unresolved}")
                raise RuntimeError(f"Circular or missing dependencies: {missing_deps}")

            # Sort ready services by priority
            ready.sort(key=lambda name: self.services[name].priority.value)

            # Add to ordered list and remove from remaining
            for service_name in ready:
                ordered.append(service_name)
                remaining.remove(service_name)

        return ordered

    async def _start_health_monitoring(self) -> None:
        """Start health monitoring task."""
        if self._health_check_task is not None:
            return

        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        self.logger.info("Health monitoring started")

    async def _stop_health_monitoring(self) -> None:
        """Stop health monitoring task."""
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            self.logger.info("Health monitoring stopped")

    async def _health_monitor_loop(self) -> None:
        """Health monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                await self._check_all_health()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)  # Short delay before retry

    async def _check_all_health(self) -> None:
        """Check health of all services."""
        for service_name, service in self.services.items():
            if service.state != ServiceState.RUNNING:
                continue

            if service.health_check is None:
                continue

            try:
                is_healthy = service.health_check()
                if not is_healthy:
                    self.logger.warning(f"Service health check failed: {service_name}", service=service_name)
                    service.error_count += 1
                    # Could implement auto-restart logic here
            except Exception as e:
                self.logger.error(f"Health check error for {service_name}: {e}", service=service_name, error=str(e))
                service.error_count += 1
                service.last_error = e

    def get_service_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific service."""
        if name not in self.services:
            return None

        service = self.services[name]
        status = {
            "name": name,
            "state": service.state.value,
            "priority": service.priority.name,
            "dependencies": list(service.dependencies),
            "error_count": service.error_count,
            "last_error": str(service.last_error) if service.last_error else None
        }

        # Get additional status from service if available
        if hasattr(service.instance, 'get_status'):
            try:
                service_status = service.instance.get_status()
                if isinstance(service_status, dict):
                    status.update(service_status)
            except Exception as e:
                self.logger.error(f"Error getting service status for {name}: {e}")

        return status

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services."""
        return {name: self.get_service_status(name) for name in self.services}

    def get_healthy_services(self) -> List[str]:
        """Get list of healthy service names."""
        healthy = []
        for name, service in self.services.items():
            if service.state == ServiceState.RUNNING and service.error_count == 0:
                healthy.append(name)
        return healthy

    def get_failed_services(self) -> List[str]:
        """Get list of failed service names."""
        failed = []
        for name, service in self.services.items():
            if service.state in [ServiceState.ERROR, ServiceState.FAILED]:
                failed.append(name)
        return failed