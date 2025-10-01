"""Provider interface protocols for FazzTV."""

from typing import Protocol, Any, Dict, List, Optional, Union
from abc import abstractmethod

from fazztv.providers.base import ModelCapability, ModelInfo, ProviderConfig


class ConfigurationProtocol(Protocol):
    """Protocol for configurable components."""

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the configuration."""
        ...

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        ...


class ValidationProtocol(Protocol):
    """Protocol for components that need validation."""

    @abstractmethod
    def validate(self) -> bool:
        """Validate the component state."""
        ...

    @abstractmethod
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors."""
        ...


class CacheableProtocol(Protocol):
    """Protocol for cacheable components."""

    @abstractmethod
    def get_cache_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate cache key for given parameters."""
        ...

    @abstractmethod
    def should_cache(self, *args: Any, **kwargs: Any) -> bool:
        """Determine if result should be cached."""
        ...


class LoggableProtocol(Protocol):
    """Protocol for components with logging capabilities."""

    @abstractmethod
    def log_operation(self, operation: str, **context: Any) -> None:
        """Log an operation with context."""
        ...

    @abstractmethod
    def log_error(self, error: Exception, **context: Any) -> None:
        """Log an error with context."""
        ...


class ProviderProtocol(Protocol):
    """Protocol defining the interface for AI providers."""

    config: ProviderConfig

    @abstractmethod
    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """Send a query to the provider."""
        ...

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models."""
        ...

    @abstractmethod
    def check_availability(self) -> bool:
        """Check if provider is available."""
        ...

    @abstractmethod
    def supports_capability(self, capability: ModelCapability) -> bool:
        """Check if provider supports a capability."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        ...

    @abstractmethod
    def get_default_model(self) -> Optional[str]:
        """Get default model."""
        ...


class EnhancedProviderProtocol(ProviderProtocol, ConfigurationProtocol, ValidationProtocol, CacheableProtocol, LoggableProtocol):
    """Enhanced provider protocol with all capabilities."""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """Send a chat completion request."""
        ...

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs: Any
    ) -> Optional[str]:
        """Generate text completion."""
        ...

    @abstractmethod
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """Translate text."""
        ...

    @abstractmethod
    def summarize(
        self,
        content: str,
        max_length: int = 100,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """Summarize content."""
        ...

    @abstractmethod
    def moderate_content(
        self,
        content: str,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Moderate content for safety."""
        ...


class ProviderManagerProtocol(Protocol):
    """Protocol for provider management."""

    @abstractmethod
    def register_provider(self, provider: ProviderProtocol) -> None:
        """Register a provider."""
        ...

    @abstractmethod
    def get_provider(self, name: str) -> Optional[ProviderProtocol]:
        """Get a provider by name."""
        ...

    @abstractmethod
    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        ...

    @abstractmethod
    def get_best_provider(self, capability: ModelCapability) -> Optional[ProviderProtocol]:
        """Get the best provider for a specific capability."""
        ...