"""Backward compatibility wrapper for OpenRouter client."""

from typing import Optional, Dict, Any
from loguru import logger

from fazztv.providers import get_provider_manager, ModelCapability


class OpenRouterClient:
    """Backward-compatible OpenRouter client using the new provider system."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenRouter client with backward compatibility.

        Args:
            api_key: Optional API key (uses settings if not provided)
        """
        # Initialize the provider manager
        self.manager = get_provider_manager()

        # Store API key if provided (for compatibility)
        self.api_key = api_key

        # Set defaults for backward compatibility
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"

        logger.info("OpenRouterClient initialized with provider system")

    def get_tax_info(self, artist: str) -> str:
        """
        Get tax information about an artist.

        Args:
            artist: Artist name

        Returns:
            Tax information text
        """
        prompt = (
            f"Provide a concise summary of {artist}'s tax problems, "
            "including key dates, fines, amounts, or relevant penalties."
        )

        response = self.query(prompt)
        return response if response else f"Tax information unavailable for {artist}"

    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Send a query to OpenRouter.

        Args:
            prompt: The prompt to send
            model: Model to use (defaults to free model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate

        Returns:
            Response text or None if error
        """
        return self.manager.query_with_fallback(
            prompt,
            preferred_provider="openrouter",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def generate_commentary(
        self,
        topic: str,
        style: str = "informative",
        length: int = 200
    ) -> Optional[str]:
        """
        Generate commentary on a topic.

        Args:
            topic: Topic to comment on
            style: Style of commentary (informative, humorous, serious)
            length: Approximate length in words

        Returns:
            Generated commentary or None
        """
        prompt = (
            f"Generate {style} commentary about {topic}. "
            f"Keep it approximately {length} words. "
            "Be engaging and suitable for a video overlay."
        )

        return self.query(prompt, max_tokens=length * 2)

    def summarize_content(
        self,
        content: str,
        max_length: int = 100
    ) -> Optional[str]:
        """
        Summarize content to a specific length.

        Args:
            content: Content to summarize
            max_length: Maximum length in words

        Returns:
            Summarized content or None
        """
        # Try to find a provider with summarization capability
        providers = self.manager.registry.find_providers_by_capability(
            ModelCapability.SUMMARIZATION
        )

        if providers:
            provider = providers[0]
            return provider.summarize(content, max_length)

        # Fallback to prompt-based summarization
        prompt = (
            f"Summarize the following content in {max_length} words or less:\n\n"
            f"{content}"
        )

        return self.query(prompt, temperature=0.3, max_tokens=max_length * 2)

    def translate_text(
        self,
        text: str,
        target_language: str = "Spanish"
    ) -> Optional[str]:
        """
        Translate text to another language.

        Args:
            text: Text to translate
            target_language: Target language

        Returns:
            Translated text or None
        """
        # Try to find a provider with translation capability
        providers = self.manager.registry.find_providers_by_capability(
            ModelCapability.TRANSLATION
        )

        if providers:
            provider = providers[0]
            return provider.translate(text, target_language)

        # Fallback to prompt-based translation
        prompt = f"Translate the following to {target_language}:\n\n{text}"
        return self.query(prompt, temperature=0.3)

    def check_content_safety(
        self,
        content: str
    ) -> Dict[str, Any]:
        """
        Check if content is safe/appropriate.

        Args:
            content: Content to check

        Returns:
            Dictionary with safety assessment
        """
        # Try to find a provider with moderation capability
        providers = self.manager.registry.find_providers_by_capability(
            ModelCapability.MODERATION
        )

        if providers:
            provider = providers[0]
            return provider.moderate_content(content)

        # Fallback to prompt-based moderation
        prompt = (
            "Analyze the following content for safety and appropriateness. "
            "Return a JSON response with fields: "
            "safe (boolean), concerns (list), rating (G/PG/PG-13/R).\n\n"
            f"{content}"
        )

        response = self.query(prompt, temperature=0.1)

        if response:
            try:
                import json
                # Try to extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except Exception as e:
                logger.error(f"Failed to parse safety check response: {e}")

        return {
            "safe": True,
            "concerns": [],
            "rating": "Unknown"
        }