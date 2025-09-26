"""Tests for provider registry."""

import pytest
from unittest.mock import Mock, MagicMock
from fazztv.providers import (
    ProviderRegistry,
    BaseProvider,
    ProviderConfig,
    ModelCapability,
    ModelInfo
)


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def __init__(self, config):
        super().__init__(config)
        self.available = True

    def query(self, prompt, model=None, **kwargs):
        return f"Response from {self.config.name}"

    def list_models(self):
        return [
            ModelInfo(
                id=f"{self.config.name}-model",
                name=f"{self.config.name.title()} Model",
                provider=self.config.name,
                capabilities=self.config.capabilities or [],
                free_tier=True
            )
        ]

    def check_availability(self):
        return self.available


class TestProviderRegistry:
    """Test ProviderRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ProviderRegistry()
        assert len(registry.list_providers()) == 0

    def test_register_provider_class(self):
        """Test registering a provider class."""
        registry = ProviderRegistry()
        registry.register_provider_class("mock", MockProvider)

        assert "mock" in registry._provider_classes
        assert registry._provider_classes["mock"] == MockProvider

    def test_register_invalid_class_raises_error(self):
        """Test registering invalid class raises error."""
        registry = ProviderRegistry()

        class NotAProvider:
            pass

        with pytest.raises(ValueError):
            registry.register_provider_class("invalid", NotAProvider)

    def test_add_provider(self):
        """Test adding a provider instance."""
        registry = ProviderRegistry()
        registry.register_provider_class("mock", MockProvider)

        config = ProviderConfig(name="mock")
        registry.add_provider(config)

        assert "mock" in registry.list_providers()
        assert registry.get_provider("mock") is not None

    def test_add_provider_with_class(self):
        """Test adding provider with explicit class."""
        registry = ProviderRegistry()

        config = ProviderConfig(name="test")
        registry.add_provider(config, MockProvider)

        assert "test" in registry.list_providers()

    def test_add_provider_without_registered_class_raises_error(self):
        """Test adding provider without registered class."""
        registry = ProviderRegistry()

        config = ProviderConfig(name="unknown")
        with pytest.raises(ValueError):
            registry.add_provider(config)

    def test_get_provider(self):
        """Test getting a provider by name."""
        registry = ProviderRegistry()
        config = ProviderConfig(name="test")
        registry.add_provider(config, MockProvider)

        provider = registry.get_provider("test")
        assert provider is not None
        assert provider.get_name() == "test"

        # Non-existent provider
        assert registry.get_provider("nonexistent") is None

    def test_list_providers(self):
        """Test listing all providers."""
        registry = ProviderRegistry()

        configs = [
            ProviderConfig(name="provider1"),
            ProviderConfig(name="provider2"),
            ProviderConfig(name="provider3")
        ]

        for config in configs:
            registry.add_provider(config, MockProvider)

        providers = registry.list_providers()
        assert len(providers) == 3
        assert "provider1" in providers
        assert "provider2" in providers
        assert "provider3" in providers

    def test_get_available_providers(self):
        """Test getting available providers."""
        registry = ProviderRegistry()

        # Add available provider
        config1 = ProviderConfig(name="available")
        registry.add_provider(config1, MockProvider)

        # Add unavailable provider
        config2 = ProviderConfig(name="unavailable")
        registry.add_provider(config2, MockProvider)
        provider2 = registry.get_provider("unavailable")
        provider2.available = False

        available = registry.get_available_providers()
        assert len(available) == 1
        assert available[0].get_name() == "available"

    def test_find_providers_by_capability(self):
        """Test finding providers by capability."""
        registry = ProviderRegistry()

        config1 = ProviderConfig(
            name="text_provider",
            capabilities=[ModelCapability.TEXT_GENERATION]
        )
        config2 = ProviderConfig(
            name="chat_provider",
            capabilities=[ModelCapability.CHAT]
        )
        config3 = ProviderConfig(
            name="multi_provider",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CHAT
            ]
        )

        registry.add_provider(config1, MockProvider)
        registry.add_provider(config2, MockProvider)
        registry.add_provider(config3, MockProvider)

        # Find text generation providers
        text_providers = registry.find_providers_by_capability(
            ModelCapability.TEXT_GENERATION
        )
        assert len(text_providers) == 2
        names = [p.get_name() for p in text_providers]
        assert "text_provider" in names
        assert "multi_provider" in names

        # Find chat providers
        chat_providers = registry.find_providers_by_capability(
            ModelCapability.CHAT
        )
        assert len(chat_providers) == 2
        names = [p.get_name() for p in chat_providers]
        assert "chat_provider" in names
        assert "multi_provider" in names

    def test_get_all_models(self):
        """Test getting all models from providers."""
        registry = ProviderRegistry()

        configs = [
            ProviderConfig(name="provider1"),
            ProviderConfig(name="provider2")
        ]

        for config in configs:
            registry.add_provider(config, MockProvider)

        models = registry.get_all_models()
        assert len(models) == 2
        assert models[0].provider == "provider1"
        assert models[1].provider == "provider2"

    def test_find_models_by_capability(self):
        """Test finding models by capability."""
        registry = ProviderRegistry()

        config1 = ProviderConfig(
            name="text_provider",
            capabilities=[ModelCapability.TEXT_GENERATION]
        )
        config2 = ProviderConfig(
            name="chat_provider",
            capabilities=[ModelCapability.CHAT]
        )

        registry.add_provider(config1, MockProvider)
        registry.add_provider(config2, MockProvider)

        text_models = registry.find_models_by_capability(
            ModelCapability.TEXT_GENERATION
        )
        assert len(text_models) == 1
        assert text_models[0].provider == "text_provider"

        chat_models = registry.find_models_by_capability(
            ModelCapability.CHAT
        )
        assert len(chat_models) == 1
        assert chat_models[0].provider == "chat_provider"

    def test_get_cheapest_model(self):
        """Test getting cheapest model."""
        registry = ProviderRegistry()

        # Create mock providers with different costs
        class CostProvider(MockProvider):
            def list_models(self):
                if self.config.name == "expensive":
                    return [
                        ModelInfo(
                            id="expensive-model",
                            name="Expensive Model",
                            provider=self.config.name,
                            capabilities=self.config.capabilities or [],
                            cost_per_token=0.01,
                            free_tier=False
                        )
                    ]
                elif self.config.name == "cheap":
                    return [
                        ModelInfo(
                            id="cheap-model",
                            name="Cheap Model",
                            provider=self.config.name,
                            capabilities=self.config.capabilities or [],
                            cost_per_token=0.001,
                            free_tier=False
                        )
                    ]
                else:  # free
                    return [
                        ModelInfo(
                            id="free-model",
                            name="Free Model",
                            provider=self.config.name,
                            capabilities=self.config.capabilities or [],
                            cost_per_token=0,
                            free_tier=True
                        )
                    ]

        configs = [
            ProviderConfig(name="expensive"),
            ProviderConfig(name="cheap"),
            ProviderConfig(name="free")
        ]

        for config in configs:
            registry.add_provider(config, CostProvider)

        # Get cheapest model (should be free)
        cheapest = registry.get_cheapest_model()
        assert cheapest.id == "free-model"

        # Get cheapest non-free model
        cheapest_paid = registry.get_cheapest_model(free_only=False)
        assert cheapest_paid.id == "free-model"  # Still free since it's cheapest

        # Get free model only
        free_model = registry.get_cheapest_model(free_only=True)
        assert free_model.id == "free-model"
        assert free_model.free_tier is True

    def test_remove_provider(self):
        """Test removing a provider."""
        registry = ProviderRegistry()

        config = ProviderConfig(name="test")
        registry.add_provider(config, MockProvider)

        assert "test" in registry.list_providers()

        # Remove provider
        result = registry.remove_provider("test")
        assert result is True
        assert "test" not in registry.list_providers()

        # Try to remove non-existent provider
        result = registry.remove_provider("nonexistent")
        assert result is False

    def test_clear_registry(self):
        """Test clearing all providers."""
        registry = ProviderRegistry()

        configs = [
            ProviderConfig(name="provider1"),
            ProviderConfig(name="provider2")
        ]

        for config in configs:
            registry.add_provider(config, MockProvider)

        assert len(registry.list_providers()) == 2

        registry.clear()
        assert len(registry.list_providers()) == 0

    def test_get_summary(self):
        """Test getting registry summary."""
        registry = ProviderRegistry()
        registry.register_provider_class("mock", MockProvider)

        config = ProviderConfig(
            name="test",
            capabilities=[ModelCapability.TEXT_GENERATION],
            default_model="test-model"
        )
        registry.add_provider(config, MockProvider)

        summary = registry.get_summary()

        assert summary["total_providers"] == 1
        assert summary["available_providers"] == 1
        assert "mock" in summary["registered_classes"]
        assert "test" in summary["providers"]
        assert summary["providers"]["test"]["available"] is True
        assert summary["providers"]["test"]["default_model"] == "test-model"