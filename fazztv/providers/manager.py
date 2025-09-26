"""Provider manager for orchestrating multi-provider operations."""

from typing import Optional, List, Dict, Any
from loguru import logger

from .base import BaseProvider, ModelCapability, ModelInfo
from .registry import ProviderRegistry


class ProviderManager:
    """Manager for coordinating operations across multiple providers."""

    def __init__(self, registry: Optional[ProviderRegistry] = None):
        """
        Initialize the provider manager.

        Args:
            registry: Provider registry (creates new one if not provided)
        """
        self.registry = registry or ProviderRegistry()
        self.fallback_enabled = True
        self.load_balancing = False
        self._request_counts: Dict[str, int] = {}

    def query_with_fallback(
        self,
        prompt: str,
        preferred_provider: Optional[str] = None,
        capability: Optional[ModelCapability] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Query providers with automatic fallback.

        Args:
            prompt: The prompt to send
            preferred_provider: Preferred provider name
            capability: Required capability
            **kwargs: Additional parameters

        Returns:
            Response text or None if all providers fail
        """
        providers = self._get_ordered_providers(preferred_provider, capability)

        for provider in providers:
            try:
                logger.debug(f"Trying provider: {provider.get_name()}")
                response = provider.query(prompt, **kwargs)

                if response:
                    self._track_usage(provider.get_name())
                    return response

                logger.warning(f"Provider {provider.get_name()} returned empty response")

            except Exception as e:
                logger.error(f"Provider {provider.get_name()} failed: {e}")

                if not self.fallback_enabled:
                    return None

        logger.error("All providers failed")
        return None

    def chat_with_fallback(
        self,
        messages: List[Dict[str, str]],
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Send chat request with automatic fallback.

        Args:
            messages: Chat messages
            preferred_provider: Preferred provider name
            **kwargs: Additional parameters

        Returns:
            Response text or None
        """
        providers = self._get_ordered_providers(
            preferred_provider,
            ModelCapability.CHAT
        )

        for provider in providers:
            try:
                logger.debug(f"Trying chat with provider: {provider.get_name()}")
                response = provider.chat(messages, **kwargs)

                if response:
                    self._track_usage(provider.get_name())
                    return response

            except Exception as e:
                logger.error(f"Chat failed with {provider.get_name()}: {e}")

                if not self.fallback_enabled:
                    return None

        logger.error("All providers failed for chat")
        return None

    def find_best_provider(
        self,
        capability: ModelCapability,
        prefer_free: bool = True
    ) -> Optional[BaseProvider]:
        """
        Find the best provider for a given capability.

        Args:
            capability: Required capability
            prefer_free: Prefer free tier models

        Returns:
            Best provider or None
        """
        providers = self.registry.find_providers_by_capability(capability)

        if not providers:
            return None

        if prefer_free:
            # Try to find a provider with free models
            for provider in providers:
                models = provider.list_models()
                if any(m.free_tier for m in models):
                    return provider

        # Return the least used provider for load balancing
        if self.load_balancing:
            return self._get_least_used_provider(providers)

        return providers[0]

    def compare_responses(
        self,
        prompt: str,
        providers: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        Compare responses from multiple providers.

        Args:
            prompt: The prompt to send
            providers: List of provider names (uses all if None)
            **kwargs: Additional parameters

        Returns:
            Dictionary mapping provider names to responses
        """
        if providers is None:
            provider_instances = self.registry.get_available_providers()
        else:
            provider_instances = [
                self.registry.get_provider(name)
                for name in providers
                if self.registry.get_provider(name)
            ]

        responses = {}
        for provider in provider_instances:
            try:
                response = provider.query(prompt, **kwargs)
                if response:
                    responses[provider.get_name()] = response
                    self._track_usage(provider.get_name())
            except Exception as e:
                logger.error(f"Error querying {provider.get_name()}: {e}")
                responses[provider.get_name()] = f"Error: {str(e)}"

        return responses

    def batch_query(
        self,
        prompts: List[str],
        provider: Optional[str] = None,
        **kwargs
    ) -> List[Optional[str]]:
        """
        Process multiple prompts in batch.

        Args:
            prompts: List of prompts
            provider: Provider name (uses best available if None)
            **kwargs: Additional parameters

        Returns:
            List of responses
        """
        if provider:
            provider_instance = self.registry.get_provider(provider)
            if not provider_instance:
                logger.error(f"Provider {provider} not found")
                return [None] * len(prompts)
        else:
            provider_instance = self.find_best_provider(ModelCapability.TEXT_GENERATION)
            if not provider_instance:
                logger.error("No suitable provider found")
                return [None] * len(prompts)

        responses = []
        for prompt in prompts:
            try:
                response = provider_instance.query(prompt, **kwargs)
                responses.append(response)
                self._track_usage(provider_instance.get_name())
            except Exception as e:
                logger.error(f"Batch query failed for prompt: {e}")
                responses.append(None)

        return responses

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Usage statistics
        """
        return {
            "request_counts": self._request_counts.copy(),
            "total_requests": sum(self._request_counts.values()),
            "providers_used": len(self._request_counts),
            "fallback_enabled": self.fallback_enabled,
            "load_balancing": self.load_balancing
        }

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self._request_counts.clear()
        logger.info("Usage statistics reset")

    def enable_fallback(self, enabled: bool = True) -> None:
        """Enable or disable automatic fallback."""
        self.fallback_enabled = enabled
        logger.info(f"Fallback {'enabled' if enabled else 'disabled'}")

    def enable_load_balancing(self, enabled: bool = True) -> None:
        """Enable or disable load balancing."""
        self.load_balancing = enabled
        logger.info(f"Load balancing {'enabled' if enabled else 'disabled'}")

    def _get_ordered_providers(
        self,
        preferred: Optional[str],
        capability: Optional[ModelCapability]
    ) -> List[BaseProvider]:
        """
        Get ordered list of providers.

        Args:
            preferred: Preferred provider name
            capability: Required capability

        Returns:
            Ordered list of providers
        """
        providers = []

        # Add preferred provider first
        if preferred:
            provider = self.registry.get_provider(preferred)
            if provider and provider.check_availability():
                if not capability or provider.supports_capability(capability):
                    providers.append(provider)

        # Add other available providers
        if capability:
            other_providers = self.registry.find_providers_by_capability(capability)
        else:
            other_providers = self.registry.get_available_providers()

        for provider in other_providers:
            if provider not in providers:
                providers.append(provider)

        # Sort by usage if load balancing is enabled
        if self.load_balancing and len(providers) > 1:
            providers.sort(key=lambda p: self._request_counts.get(p.get_name(), 0))

        return providers

    def _get_least_used_provider(
        self,
        providers: List[BaseProvider]
    ) -> BaseProvider:
        """
        Get the least used provider.

        Args:
            providers: List of providers

        Returns:
            Least used provider
        """
        if not providers:
            raise ValueError("No providers provided")

        return min(
            providers,
            key=lambda p: self._request_counts.get(p.get_name(), 0)
        )

    def _track_usage(self, provider_name: str) -> None:
        """Track usage for a provider."""
        self._request_counts[provider_name] = self._request_counts.get(provider_name, 0) + 1