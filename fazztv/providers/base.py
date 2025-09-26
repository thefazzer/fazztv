"""Base provider interface for multi-model hosting."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from loguru import logger


class ModelCapability(Enum):
    """Model capabilities enum."""
    TEXT_GENERATION = "text_generation"
    CHAT = "chat"
    CODE_GENERATION = "code_generation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"
    AUDIO_GENERATION = "audio_generation"
    VIDEO_GENERATION = "video_generation"
    MODERATION = "moderation"


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    custom_headers: Optional[Dict[str, str]] = None
    capabilities: Optional[List[ModelCapability]] = None

    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.name:
            return False
        return True

    def __post_init__(self):
        """Post-initialization processing."""
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class ModelInfo:
    """Information about a specific model."""
    id: str
    name: str
    provider: str
    capabilities: List[ModelCapability]
    context_length: Optional[int] = None
    cost_per_token: Optional[float] = None
    free_tier: bool = False
    description: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for AI model providers."""

    def __init__(self, config: ProviderConfig):
        """
        Initialize the provider.

        Args:
            config: Provider configuration
        """
        if not config.validate():
            raise ValueError(f"Invalid configuration for provider {config.name}")
        self.config = config
        logger.info(f"Initialized provider: {config.name}")

    @abstractmethod
    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Send a query to the provider.

        Args:
            prompt: The prompt to send
            model: Model to use (uses default if not specified)
            **kwargs: Additional provider-specific parameters

        Returns:
            Response text or None if error
        """
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """
        List available models for this provider.

        Returns:
            List of available models
        """
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        """
        Check if the provider is available and configured.

        Returns:
            True if provider is available
        """
        pass

    def supports_capability(self, capability: ModelCapability) -> bool:
        """
        Check if provider supports a specific capability.

        Args:
            capability: The capability to check

        Returns:
            True if capability is supported
        """
        if self.config.capabilities:
            return capability in self.config.capabilities
        return False

    def get_name(self) -> str:
        """Get provider name."""
        return self.config.name

    def get_default_model(self) -> Optional[str]:
        """Get default model for this provider."""
        return self.config.default_model

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Send a chat completion request.

        Args:
            messages: List of chat messages
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Response text or None
        """
        if not self.supports_capability(ModelCapability.CHAT):
            logger.warning(f"Provider {self.get_name()} does not support chat")
            return None

        # Convert messages to prompt if provider doesn't support chat format
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        return self.query(prompt, model=model, **kwargs)

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text completion.

        Args:
            prompt: The prompt
            model: Model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated text or None
        """
        if not self.supports_capability(ModelCapability.TEXT_GENERATION):
            logger.warning(f"Provider {self.get_name()} does not support text generation")
            return None

        return self.query(
            prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Translate text.

        Args:
            text: Text to translate
            target_language: Target language
            source_language: Source language (auto-detect if None)
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Translated text or None
        """
        if not self.supports_capability(ModelCapability.TRANSLATION):
            logger.warning(f"Provider {self.get_name()} does not support translation")
            return None

        source_part = f"from {source_language} " if source_language else ""
        prompt = f"Translate the following {source_part}to {target_language}:\n\n{text}"

        return self.query(prompt, model=model, temperature=0.3, **kwargs)

    def summarize(
        self,
        content: str,
        max_length: int = 100,
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Summarize content.

        Args:
            content: Content to summarize
            max_length: Maximum length in words
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Summary or None
        """
        if not self.supports_capability(ModelCapability.SUMMARIZATION):
            logger.warning(f"Provider {self.get_name()} does not support summarization")
            return None

        prompt = (
            f"Summarize the following content in {max_length} words or less:\n\n"
            f"{content}"
        )

        return self.query(
            prompt,
            model=model,
            temperature=0.3,
            max_tokens=max_length * 2,
            **kwargs
        )

    def moderate_content(
        self,
        content: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Check content for safety/appropriateness.

        Args:
            content: Content to check
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Moderation results
        """
        if not self.supports_capability(ModelCapability.MODERATION):
            logger.warning(f"Provider {self.get_name()} does not support moderation")
            return {"safe": True, "concerns": [], "rating": "Unknown"}

        prompt = (
            "Analyze the following content for safety and appropriateness. "
            "Return a JSON response with fields: "
            "safe (boolean), concerns (list), rating (G/PG/PG-13/R).\n\n"
            f"{content}"
        )

        response = self.query(prompt, model=model, temperature=0.1, **kwargs)

        if response:
            try:
                import json
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except Exception as e:
                logger.error(f"Failed to parse moderation response: {e}")

        return {"safe": True, "concerns": [], "rating": "Unknown"}