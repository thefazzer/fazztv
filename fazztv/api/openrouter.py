"""OpenRouter API client for FazzTV - Compatibility layer."""

from typing import Optional, Dict, Any
from loguru import logger

# Import the compatibility wrapper
from .openrouter_compat import OpenRouterClient


# The OpenRouterClient is now imported from the compatibility module
# which provides backward compatibility while using the new provider system
__all__ = ['OpenRouterClient']


# Add a deprecation notice function that can be called
def _deprecation_notice():
    """Log deprecation notice for direct usage."""
    logger.warning(
        "Direct usage of fazztv.api.openrouter is deprecated. "
        "Please use fazztv.providers.get_provider_manager() for new code."
    )