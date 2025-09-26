"""Tests for base provider functionality."""

import pytest
from unittest.mock import Mock, patch
from fazztv.providers import (
    BaseProvider,
    ProviderConfig,
    ModelCapability,
    ModelInfo
)


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def query(self, prompt, model=None, **kwargs):
        return f"Response to: {prompt}"

    def list_models(self):
        return [
            ModelInfo(
                id="mock-model",
                name="Mock Model",
                provider="mock",
                capabilities=[ModelCapability.TEXT_GENERATION]
            )
        ]

    def check_availability(self):
        return True


class TestProviderConfig:
    """Test ProviderConfig class."""

    def test_config_creation(self):
        """Test creating a provider configuration."""
        config = ProviderConfig(
            name="test",
            api_key="test-key",
            base_url="http://test.com",
            default_model="test-model"
        )

        assert config.name == "test"
        assert config.api_key == "test-key"
        assert config.base_url == "http://test.com"
        assert config.default_model == "test-model"

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = ProviderConfig(name="test")
        assert config.validate() is True

        # Invalid config (no name)
        config = ProviderConfig(name="")
        assert config.validate() is False

    def test_config_defaults(self):
        """Test default configuration values."""
        config = ProviderConfig(name="test")

        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.custom_headers is None
        assert config.capabilities == []


class TestBaseProvider:
    """Test BaseProvider abstract class."""

    def test_provider_initialization(self):
        """Test provider initialization."""
        config = ProviderConfig(
            name="mock",
            capabilities=[ModelCapability.TEXT_GENERATION]
        )
        provider = MockProvider(config)

        assert provider.config == config
        assert provider.get_name() == "mock"

    def test_invalid_config_raises_error(self):
        """Test that invalid config raises error."""
        config = ProviderConfig(name="")

        with pytest.raises(ValueError):
            MockProvider(config)

    def test_supports_capability(self):
        """Test capability checking."""
        config = ProviderConfig(
            name="mock",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CHAT
            ]
        )
        provider = MockProvider(config)

        assert provider.supports_capability(ModelCapability.TEXT_GENERATION)
        assert provider.supports_capability(ModelCapability.CHAT)
        assert not provider.supports_capability(ModelCapability.IMAGE_GENERATION)

    def test_get_default_model(self):
        """Test getting default model."""
        config = ProviderConfig(
            name="mock",
            default_model="mock-model"
        )
        provider = MockProvider(config)

        assert provider.get_default_model() == "mock-model"

    def test_chat_method(self):
        """Test chat method."""
        config = ProviderConfig(
            name="mock",
            capabilities=[ModelCapability.CHAT]
        )
        provider = MockProvider(config)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]

        response = provider.chat(messages)
        assert response is not None

    def test_chat_without_capability(self):
        """Test chat without capability returns None."""
        config = ProviderConfig(
            name="mock",
            capabilities=[]
        )
        provider = MockProvider(config)

        messages = [{"role": "user", "content": "Hello"}]
        response = provider.chat(messages)
        assert response is None

    def test_generate_text(self):
        """Test text generation."""
        config = ProviderConfig(
            name="mock",
            capabilities=[ModelCapability.TEXT_GENERATION]
        )
        provider = MockProvider(config)

        response = provider.generate_text("Generate text")
        assert response == "Response to: Generate text"

    def test_translate(self):
        """Test translation."""
        config = ProviderConfig(
            name="mock",
            capabilities=[ModelCapability.TRANSLATION]
        )
        provider = MockProvider(config)

        response = provider.translate("Hello", "Spanish")
        assert response is not None

    def test_summarize(self):
        """Test summarization."""
        config = ProviderConfig(
            name="mock",
            capabilities=[ModelCapability.SUMMARIZATION]
        )
        provider = MockProvider(config)

        response = provider.summarize("Long text to summarize")
        assert response is not None

    def test_moderate_content(self):
        """Test content moderation."""
        config = ProviderConfig(
            name="mock",
            capabilities=[ModelCapability.MODERATION]
        )
        provider = MockProvider(config)

        result = provider.moderate_content("Content to check")
        assert isinstance(result, dict)
        assert "safe" in result
        assert "concerns" in result
        assert "rating" in result


class TestModelInfo:
    """Test ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Test creating model information."""
        model = ModelInfo(
            id="test-model",
            name="Test Model",
            provider="test",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CHAT
            ],
            context_length=4096,
            cost_per_token=0.001,
            free_tier=False,
            description="A test model"
        )

        assert model.id == "test-model"
        assert model.name == "Test Model"
        assert model.provider == "test"
        assert len(model.capabilities) == 2
        assert model.context_length == 4096
        assert model.cost_per_token == 0.001
        assert model.free_tier is False
        assert model.description == "A test model"

    def test_model_info_minimal(self):
        """Test creating model info with minimal fields."""
        model = ModelInfo(
            id="test",
            name="Test",
            provider="test",
            capabilities=[]
        )

        assert model.id == "test"
        assert model.context_length is None
        assert model.cost_per_token is None
        assert model.free_tier is False


class TestModelCapability:
    """Test ModelCapability enum."""

    def test_capability_values(self):
        """Test capability enum values."""
        assert ModelCapability.TEXT_GENERATION.value == "text_generation"
        assert ModelCapability.CHAT.value == "chat"
        assert ModelCapability.CODE_GENERATION.value == "code_generation"
        assert ModelCapability.TRANSLATION.value == "translation"
        assert ModelCapability.SUMMARIZATION.value == "summarization"
        assert ModelCapability.EMBEDDING.value == "embedding"
        assert ModelCapability.IMAGE_GENERATION.value == "image_generation"
        assert ModelCapability.MODERATION.value == "moderation"

    def test_capability_from_string(self):
        """Test creating capability from string."""
        cap = ModelCapability("text_generation")
        assert cap == ModelCapability.TEXT_GENERATION

        cap = ModelCapability("chat")
        assert cap == ModelCapability.CHAT