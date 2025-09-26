"""Provider registry for managing multiple AI providers."""

from typing import Dict, List, Optional, Type, Any
from loguru import logger

from .base import BaseProvider, ProviderConfig, ModelCapability, ModelInfo


class ProviderRegistry:
    """Registry for managing AI model providers."""

    def __init__(self):
        """Initialize the registry."""
        self._providers: Dict[str, BaseProvider] = {}
        self._provider_classes: Dict[str, Type[BaseProvider]] = {}

    def register_provider_class(
        self,
        name: str,
        provider_class: Type[BaseProvider]
    ) -> None:
        """
        Register a provider class.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from BaseProvider)
        """
        if not issubclass(provider_class, BaseProvider):
            raise ValueError(f"{provider_class} must inherit from BaseProvider")

        self._provider_classes[name] = provider_class
        logger.info(f"Registered provider class: {name}")

    def add_provider(
        self,
        config: ProviderConfig,
        provider_class: Optional[Type[BaseProvider]] = None
    ) -> None:
        """
        Add a provider instance.

        Args:
            config: Provider configuration
            provider_class: Optional provider class (uses registered class if not provided)
        """
        if provider_class is None:
            if config.name not in self._provider_classes:
                raise ValueError(f"No registered class for provider: {config.name}")
            provider_class = self._provider_classes[config.name]

        provider = provider_class(config)
        self._providers[config.name] = provider
        logger.info(f"Added provider instance: {config.name}")

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """
        Get a provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None
        """
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """
        List all registered providers.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def get_available_providers(self) -> List[BaseProvider]:
        """
        Get all available (configured and accessible) providers.

        Returns:
            List of available providers
        """
        available = []
        for name, provider in self._providers.items():
            try:
                if provider.check_availability():
                    available.append(provider)
                else:
                    logger.debug(f"Provider {name} is not available")
            except Exception as e:
                logger.error(f"Error checking availability for {name}: {e}")
        return available

    def find_providers_by_capability(
        self,
        capability: ModelCapability
    ) -> List[BaseProvider]:
        """
        Find providers that support a specific capability.

        Args:
            capability: The capability to search for

        Returns:
            List of providers supporting the capability
        """
        matching = []
        for provider in self._providers.values():
            if provider.supports_capability(capability):
                matching.append(provider)
        return matching

    def get_all_models(self) -> List[ModelInfo]:
        """
        Get all available models from all providers.

        Returns:
            List of all available models
        """
        all_models = []
        for provider in self.get_available_providers():
            try:
                models = provider.list_models()
                all_models.extend(models)
            except Exception as e:
                logger.error(f"Error listing models for {provider.get_name()}: {e}")
        return all_models

    def find_models_by_capability(
        self,
        capability: ModelCapability
    ) -> List[ModelInfo]:
        """
        Find models that support a specific capability.

        Args:
            capability: The capability to search for

        Returns:
            List of models supporting the capability
        """
        matching_models = []
        for model in self.get_all_models():
            if capability in model.capabilities:
                matching_models.append(model)
        return matching_models

    def get_cheapest_model(
        self,
        capability: Optional[ModelCapability] = None,
        free_only: bool = False
    ) -> Optional[ModelInfo]:
        """
        Get the cheapest model, optionally filtered by capability.

        Args:
            capability: Optional capability filter
            free_only: Only return free models

        Returns:
            Cheapest model or None
        """
        models = self.get_all_models()

        if capability:
            models = [m for m in models if capability in m.capabilities]

        if free_only:
            models = [m for m in models if m.free_tier]

        if not models:
            return None

        # Sort by cost (free models first, then by cost)
        models.sort(key=lambda m: (
            not m.free_tier,
            m.cost_per_token if m.cost_per_token else float('inf')
        ))

        return models[0]

    def remove_provider(self, name: str) -> bool:
        """
        Remove a provider from the registry.

        Args:
            name: Provider name

        Returns:
            True if removed, False if not found
        """
        if name in self._providers:
            del self._providers[name]
            logger.info(f"Removed provider: {name}")
            return True
        return False

    def clear(self) -> None:
        """Clear all providers from the registry."""
        self._providers.clear()
        logger.info("Cleared all providers from registry")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the registry state.

        Returns:
            Dictionary with registry information
        """
        return {
            "total_providers": len(self._providers),
            "available_providers": len(self.get_available_providers()),
            "registered_classes": list(self._provider_classes.keys()),
            "providers": {
                name: {
                    "available": provider.check_availability(),
                    "capabilities": [c.value for c in provider.config.capabilities or []],
                    "default_model": provider.get_default_model()
                }
                for name, provider in self._providers.items()
            }
        }