"""OpenAI provider implementation."""

import requests
from typing import Optional, List, Dict, Any
from loguru import logger

from .base import BaseProvider, ProviderConfig, ModelCapability, ModelInfo


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI API."""

    def __init__(self, config: ProviderConfig):
        """Initialize OpenAI provider."""
        # Validate API key
        if not config.api_key:
            raise ValueError("OpenAI API key is required")

        if not config.base_url:
            config.base_url = "https://api.openai.com/v1"
        if not config.default_model:
            config.default_model = "gpt-3.5-turbo"
        if not config.capabilities:
            config.capabilities = [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CHAT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.TRANSLATION,
                ModelCapability.SUMMARIZATION,
                ModelCapability.EMBEDDING,
                ModelCapability.MODERATION
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
        """Send a query to OpenAI."""
        if not self.config.api_key:
            logger.error("OpenAI API key not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        if self.config.custom_headers:
            headers.update(self.config.custom_headers)

        model_name = model or self.config.default_model

        # Use chat completions for chat models
        if "gpt" in model_name.lower():
            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            endpoint = "chat/completions"
        else:
            # Use completions for other models
            data = {
                "model": model_name,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            endpoint = "completions"

        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in data:
                data[key] = value

        try:
            response = requests.post(
                f"{self.config.base_url}/{endpoint}",
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()

            if endpoint == "chat/completions":
                if "choices" in result and result["choices"]:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    if content:
                        logger.debug(f"OpenAI response: {content[:100]}...")
                        return content
            else:
                if "choices" in result and result["choices"]:
                    content = result["choices"][0].get("text", "")
                    if content:
                        logger.debug(f"OpenAI response: {content[:100]}...")
                        return content

            logger.error("No content in OpenAI response")
            return None

        except requests.exceptions.Timeout:
            logger.error(f"OpenAI request timed out after {self.config.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying OpenAI: {e}")
            return None

    def list_models(self) -> List[ModelInfo]:
        """List available models from OpenAI."""
        try:
            model_data = self._fetch_models_from_api()
            return self._parse_models_response(model_data)
        except Exception as e:
            logger.error(f"Failed to list OpenAI models: {e}")
            return self._get_default_models()

    def _fetch_models_from_api(self) -> Dict[str, Any]:
        """Fetch raw model data from OpenAI API."""
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
        return response.json()

    def _parse_models_response(self, data: Dict[str, Any]) -> List[ModelInfo]:
        """Parse API response and create ModelInfo objects."""
        models = []
        for model_data in data.get("data", []):
            model_id = model_data.get("id", "")
            if model_id:
                model = self._create_model_info(model_id)
                models.append(model)
        return models

    def _create_model_info(self, model_id: str) -> ModelInfo:
        """Create ModelInfo object from model ID."""
        return ModelInfo(
            model_id=model_id,
            name=model_id,
            provider="openai",
            capabilities=self._get_model_capabilities(model_id),
            context_length=self._get_context_length(model_id),
            cost_per_token=self._get_cost_per_token(model_id),
            free_tier=False,
            description=f"OpenAI {model_id} model"
        )

    def _get_model_capabilities(self, model_id: str) -> List[ModelCapability]:
        """Map model ID to appropriate capabilities."""
        model_lower = model_id.lower()

        if "gpt" in model_lower or "turbo" in model_lower:
            return [
                ModelCapability.CHAT,
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.TRANSLATION,
                ModelCapability.SUMMARIZATION
            ]
        elif "embedding" in model_lower:
            return [ModelCapability.EMBEDDING]
        elif "moderation" in model_lower:
            return [ModelCapability.MODERATION]
        else:
            return [ModelCapability.TEXT_GENERATION]

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for model."""
        if "gpt-3.5" in model_id:
            return 8192
        elif "gpt-4" in model_id:
            return 8192
        else:
            return 4096

    def _get_cost_per_token(self, model_id: str) -> float:
        """Estimate cost per token for model."""
        if "gpt-4" in model_id:
            return 0.002
        else:
            return 0.0002

    def _get_default_models(self) -> List[ModelInfo]:
        """Return default models when API call fails."""
        return [
            ModelInfo(
                model_id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="openai",
                capabilities=self.config.capabilities or [],
                context_length=4096,
                cost_per_token=0.0002,
                free_tier=False,
                description="Fast and efficient chat model"
            ),
            ModelInfo(
                model_id="gpt-4",
                name="GPT-4",
                provider="openai",
                capabilities=self.config.capabilities or [],
                context_length=8192,
                cost_per_token=0.002,
                free_tier=False,
                description="Most capable GPT-4 model"
            )
        ]

    def check_availability(self) -> bool:
        """Check if OpenAI is available."""
        if not self.config.api_key:
            return False

        try:
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
            logger.debug(f"OpenAI availability check failed: {e}")
            return False

    def get_embeddings(
        self,
        text: str,
        model: str = "text-embedding-ada-002"
    ) -> Optional[List[float]]:
        """Get embeddings for text."""
        if not self.supports_capability(ModelCapability.EMBEDDING):
            logger.warning("OpenAI provider does not support embeddings")
            return None

        if not self.config.api_key:
            logger.error("OpenAI API key not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "input": text,
            "model": model
        }

        try:
            response = requests.post(
                f"{self.config.base_url}/embeddings",
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()
            if "data" in result and result["data"]:
                return result["data"][0].get("embedding")

        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")

        return None

    def moderate_content(
        self,
        content: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Use OpenAI moderation API."""
        if not self.config.api_key:
            logger.error("OpenAI API key not configured")
            return {"safe": True, "concerns": [], "rating": "Unknown"}

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        data = {"input": content}

        try:
            response = requests.post(
                f"{self.config.base_url}/moderations",
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()
            if "results" in result and result["results"]:
                moderation = result["results"][0]
                flagged = moderation.get("flagged", False)

                concerns = []
                categories = moderation.get("categories", {})
                for category, is_flagged in categories.items():
                    if is_flagged:
                        concerns.append(category)

                # Determine rating based on flags
                rating = "G"
                if flagged:
                    if "violence" in concerns or "violence/graphic" in concerns:
                        rating = "R"
                    elif "sexual" in concerns:
                        rating = "R"
                    elif "hate" in concerns:
                        rating = "PG-13"
                    else:
                        rating = "PG"

                return {
                    "safe": not flagged,
                    "concerns": concerns,
                    "rating": rating
                }

        except Exception as e:
            logger.error(f"Failed to moderate content: {e}")

        return {"safe": True, "concerns": [], "rating": "Unknown"}