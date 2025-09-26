"""Tests for provider manager."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fazztv.providers import (
    ProviderManager,
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
        self.query_response = f"Response from {config.name}"
        self.should_fail = False

    def query(self, prompt, model=None, **kwargs):
        if self.should_fail:
            raise Exception("Provider failed")
        return self.query_response

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
        return not self.should_fail

    def chat(self, messages, model=None, **kwargs):
        if self.should_fail:
            raise Exception("Chat failed")
        return f"Chat response from {self.config.name}"


class TestProviderManager:
    """Test ProviderManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        self.manager = ProviderManager(self.registry)

        # Add mock providers
        configs = [
            ProviderConfig(
                name="provider1",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CHAT]
            ),
            ProviderConfig(
                name="provider2",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CHAT]
            ),
            ProviderConfig(
                name="provider3",
                capabilities=[ModelCapability.TEXT_GENERATION]
            )
        ]

        for config in configs:
            self.registry.add_provider(config, MockProvider)

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = ProviderManager()
        assert manager.registry is not None
        assert manager.fallback_enabled is True
        assert manager.load_balancing is False

    def test_query_with_fallback_success(self):
        """Test query with successful first provider."""
        response = self.manager.query_with_fallback("Test prompt")
        assert response == "Response from provider1"

    def test_query_with_fallback_preferred_provider(self):
        """Test query with preferred provider."""
        response = self.manager.query_with_fallback(
            "Test prompt",
            preferred_provider="provider2"
        )
        assert response == "Response from provider2"

    def test_query_with_fallback_first_fails(self):
        """Test query fallback when first provider fails."""
        provider1 = self.registry.get_provider("provider1")
        provider1.should_fail = True

        response = self.manager.query_with_fallback("Test prompt")
        assert response == "Response from provider2"

    def test_query_with_fallback_all_fail(self):
        """Test query when all providers fail."""
        for name in ["provider1", "provider2", "provider3"]:
            provider = self.registry.get_provider(name)
            provider.should_fail = True

        response = self.manager.query_with_fallback("Test prompt")
        assert response is None

    def test_query_with_fallback_disabled(self):
        """Test query with fallback disabled."""
        self.manager.fallback_enabled = False
        provider1 = self.registry.get_provider("provider1")
        provider1.should_fail = True

        response = self.manager.query_with_fallback("Test prompt")
        assert response is None

    def test_query_with_capability_filter(self):
        """Test query with capability filter."""
        # Only provider1 and provider2 have CHAT capability
        response = self.manager.query_with_fallback(
            "Test prompt",
            capability=ModelCapability.CHAT
        )
        assert response in ["Response from provider1", "Response from provider2"]

    def test_chat_with_fallback(self):
        """Test chat with fallback."""
        messages = [{"role": "user", "content": "Hello"}]
        response = self.manager.chat_with_fallback(messages)
        assert response == "Chat response from provider1"

    def test_chat_with_fallback_first_fails(self):
        """Test chat fallback when first provider fails."""
        provider1 = self.registry.get_provider("provider1")
        provider1.should_fail = True

        messages = [{"role": "user", "content": "Hello"}]
        response = self.manager.chat_with_fallback(messages)
        assert response == "Chat response from provider2"

    def test_find_best_provider(self):
        """Test finding best provider for capability."""
        provider = self.manager.find_best_provider(ModelCapability.TEXT_GENERATION)
        assert provider is not None
        assert provider.supports_capability(ModelCapability.TEXT_GENERATION)

    def test_find_best_provider_no_match(self):
        """Test finding provider for unsupported capability."""
        provider = self.manager.find_best_provider(ModelCapability.IMAGE_GENERATION)
        assert provider is None

    def test_find_best_provider_with_free_preference(self):
        """Test finding best provider preferring free tier."""
        provider = self.manager.find_best_provider(
            ModelCapability.TEXT_GENERATION,
            prefer_free=True
        )
        assert provider is not None

    def test_compare_responses(self):
        """Test comparing responses from multiple providers."""
        responses = self.manager.compare_responses("Test prompt")

        assert len(responses) == 3
        assert responses["provider1"] == "Response from provider1"
        assert responses["provider2"] == "Response from provider2"
        assert responses["provider3"] == "Response from provider3"

    def test_compare_responses_specific_providers(self):
        """Test comparing responses from specific providers."""
        responses = self.manager.compare_responses(
            "Test prompt",
            providers=["provider1", "provider3"]
        )

        assert len(responses) == 2
        assert "provider1" in responses
        assert "provider3" in responses
        assert "provider2" not in responses

    def test_compare_responses_with_failure(self):
        """Test comparing responses when some providers fail."""
        provider2 = self.registry.get_provider("provider2")
        provider2.should_fail = True

        responses = self.manager.compare_responses("Test prompt")

        assert len(responses) == 3
        assert responses["provider1"] == "Response from provider1"
        assert "Error:" in responses["provider2"]
        assert responses["provider3"] == "Response from provider3"

    def test_batch_query(self):
        """Test batch query processing."""
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        responses = self.manager.batch_query(prompts)

        assert len(responses) == 3
        assert all(r == "Response from provider1" for r in responses)

    def test_batch_query_specific_provider(self):
        """Test batch query with specific provider."""
        prompts = ["Prompt 1", "Prompt 2"]
        responses = self.manager.batch_query(prompts, provider="provider2")

        assert len(responses) == 2
        assert all(r == "Response from provider2" for r in responses)

    def test_batch_query_invalid_provider(self):
        """Test batch query with invalid provider."""
        prompts = ["Prompt 1", "Prompt 2"]
        responses = self.manager.batch_query(prompts, provider="nonexistent")

        assert len(responses) == 2
        assert all(r is None for r in responses)

    def test_batch_query_with_failure(self):
        """Test batch query with some failures."""
        provider1 = self.registry.get_provider("provider1")
        original_query = provider1.query

        def failing_query(prompt, **kwargs):
            if "2" in prompt:
                raise Exception("Query failed")
            return original_query(prompt, **kwargs)

        provider1.query = failing_query

        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        responses = self.manager.batch_query(prompts)

        assert responses[0] == "Response from provider1"
        assert responses[1] is None
        assert responses[2] == "Response from provider1"

    def test_usage_tracking(self):
        """Test usage statistics tracking."""
        # Make some queries
        self.manager.query_with_fallback("Test 1")
        self.manager.query_with_fallback("Test 2", preferred_provider="provider2")
        self.manager.query_with_fallback("Test 3")

        stats = self.manager.get_usage_stats()

        assert stats["total_requests"] == 3
        assert stats["request_counts"]["provider1"] == 2
        assert stats["request_counts"]["provider2"] == 1
        assert stats["providers_used"] == 2

    def test_reset_usage_stats(self):
        """Test resetting usage statistics."""
        # Make some queries
        self.manager.query_with_fallback("Test")

        # Reset stats
        self.manager.reset_usage_stats()
        stats = self.manager.get_usage_stats()

        assert stats["total_requests"] == 0
        assert len(stats["request_counts"]) == 0

    def test_enable_fallback(self):
        """Test enabling/disabling fallback."""
        assert self.manager.fallback_enabled is True

        self.manager.enable_fallback(False)
        assert self.manager.fallback_enabled is False

        self.manager.enable_fallback(True)
        assert self.manager.fallback_enabled is True

    def test_enable_load_balancing(self):
        """Test enabling/disabling load balancing."""
        assert self.manager.load_balancing is False

        self.manager.enable_load_balancing(True)
        assert self.manager.load_balancing is True

        self.manager.enable_load_balancing(False)
        assert self.manager.load_balancing is False

    def test_load_balancing_distribution(self):
        """Test load balancing distributes requests."""
        self.manager.enable_load_balancing(True)

        # Make multiple queries
        for _ in range(6):
            self.manager.query_with_fallback("Test")

        stats = self.manager.get_usage_stats()

        # With load balancing, requests should be distributed
        # After 6 requests, each of 3 providers should have ~2 requests
        assert stats["total_requests"] == 6
        # Check that requests are somewhat distributed
        counts = list(stats["request_counts"].values())
        assert min(counts) >= 1
        assert max(counts) <= 3