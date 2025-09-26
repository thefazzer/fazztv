"""OpenRouter provider implementation."""

import requests
from typing import Optional, List, Dict, Any
from loguru import logger

from fazztv.config import constants
from .base import BaseProvider, ProviderConfig, ModelCapability, ModelInfo


class OpenRouterProvider(BaseProvider):
    """Provider for OpenRouter API."""

    def __init__(self, config: ProviderConfig):
        """Initialize OpenRouter provider."""
        if not config.base_url:
            config.base_url = "https://openrouter.ai/api/v1"
        if not config.default_model:
            config.default_model = "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"
        if not config.capabilities:
            config.capabilities = [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CHAT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.TRANSLATION,
                ModelCapability.SUMMARIZATION
            ]
        super().__init__(config)

    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> Optional[str]:
        """Send a query to OpenRouter."""
        if not self.config.api_key:
            logger.error("OpenRouter API key not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://fazztv.com",
            "X-Title": "FazzTV"
        }

        if self.config.custom_headers:
            headers.update(self.config.custom_headers)

        data = {
            "model": model or self.config.default_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add any additional kwargs to the request
        for key, value in kwargs.items():
            if key not in data:
                data[key] = value

        try:
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()

            if "choices" in result and result["choices"]:
                content = result["choices"][0].get("message", {}).get("content", "")
                if content:
                    logger.debug(f"OpenRouter response: {content[:100]}...")
                    return content
                else:
                    logger.error("No content in OpenRouter response")
                    return None
            else:
                logger.error(f"Unexpected OpenRouter response structure: {result}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"OpenRouter request timed out after {self.config.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying OpenRouter: {e}")
            return None

    def list_models(self) -> List[ModelInfo]:
        """List available models from OpenRouter."""
        models = []

        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{self.config.base_url}/models",
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            data = response.json()

            for model_data in data.get("data", []):
                model_id = model_data.get("id", "")
                is_free = ":free" in model_id

                model = ModelInfo(
                    id=model_id,
                    name=model_data.get("name", model_id),
                    provider="openrouter",
                    capabilities=self.config.capabilities or [],
                    context_length=model_data.get("context_length"),
                    cost_per_token=0 if is_free else model_data.get("pricing", {}).get("prompt", 0),
                    free_tier=is_free,
                    description=model_data.get("description")
                )
                models.append(model)

        except Exception as e:
            logger.error(f"Failed to list OpenRouter models: {e}")
            # Return some default models
            models = [
                ModelInfo(
                    id="cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
                    name="Dolphin 3.0 Mistral 24B (Free)",
                    provider="openrouter",
                    capabilities=self.config.capabilities or [],
                    context_length=16384,
                    cost_per_token=0,
                    free_tier=True,
                    description="Free tier Mistral-based model"
                ),
                ModelInfo(
                    id="meta-llama/llama-3.2-3b-instruct:free",
                    name="Llama 3.2 3B Instruct (Free)",
                    provider="openrouter",
                    capabilities=self.config.capabilities or [],
                    context_length=8192,
                    cost_per_token=0,
                    free_tier=True,
                    description="Free tier Llama model"
                )
            ]

        return models

    def check_availability(self) -> bool:
        """Check if OpenRouter is available."""
        if not self.config.api_key:
            return False

        try:
            # Try a simple model list request
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{self.config.base_url}/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200

        except Exception as e:
            logger.debug(f"OpenRouter availability check failed: {e}")
            return False

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Send a chat completion request to OpenRouter."""
        if not self.config.api_key:
            logger.error("OpenRouter API key not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://fazztv.com",
            "X-Title": "FazzTV"
        }

        if self.config.custom_headers:
            headers.update(self.config.custom_headers)

        data = {
            "model": model or self.config.default_model,
            "messages": messages,
            **kwargs
        }

        try:
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()

            if "choices" in result and result["choices"]:
                content = result["choices"][0].get("message", {}).get("content", "")
                if content:
                    return content

        except Exception as e:
            logger.error(f"OpenRouter chat request failed: {e}")

        return None