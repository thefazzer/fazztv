"""Ollama provider for local model hosting."""

import requests
from typing import Optional, List, Dict, Any
from loguru import logger

from .base import BaseProvider, ProviderConfig, ModelCapability, ModelInfo


class OllamaProvider(BaseProvider):
    """Provider for Ollama local models."""

    def __init__(self, config: ProviderConfig):
        """Initialize Ollama provider."""
        if not config.base_url:
            config.base_url = "http://localhost:11434"
        if not config.default_model:
            config.default_model = "llama2"
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
        """Send a query to Ollama."""
        try:
            data = {
                "model": model or self.config.default_model,
                "prompt": prompt,
                "temperature": temperature,
                "num_predict": max_tokens,
                "stream": False
            }

            # Add any additional kwargs
            for key, value in kwargs.items():
                if key not in data:
                    data[key] = value

            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("response", "")

            if content:
                logger.debug(f"Ollama response: {content[:100]}...")
                return content

            logger.error("No content in Ollama response")
            return None

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.config.base_url}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.config.timeout}s")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying Ollama: {e}")
            return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Send a chat request to Ollama."""
        try:
            data = {
                "model": model or self.config.default_model,
                "messages": messages,
                "stream": False
            }

            # Add any additional kwargs
            for key, value in kwargs.items():
                if key not in data:
                    data[key] = value

            response = requests.post(
                f"{self.config.base_url}/api/chat",
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()
            message = result.get("message", {})
            content = message.get("content", "")

            if content:
                logger.debug(f"Ollama chat response: {content[:100]}...")
                return content

            logger.error("No content in Ollama chat response")
            return None

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.config.base_url}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Ollama chat request timed out after {self.config.timeout}s")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Ollama chat: {e}")
            return None

    def list_models(self) -> List[ModelInfo]:
        """List available models from Ollama."""
        models = []

        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()

            data = response.json()

            for model_data in data.get("models", []):
                model_name = model_data.get("name", "")
                model_size = model_data.get("size", 0)

                # Determine capabilities based on model name
                capabilities = [
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHAT
                ]

                if "code" in model_name.lower() or "codellama" in model_name.lower():
                    capabilities.append(ModelCapability.CODE_GENERATION)

                # Estimate context length based on model
                context_length = 4096
                if "llama2" in model_name.lower():
                    context_length = 4096
                elif "mistral" in model_name.lower():
                    context_length = 8192
                elif "mixtral" in model_name.lower():
                    context_length = 32768

                model = ModelInfo(
                    id=model_name,
                    name=model_name,
                    provider="ollama",
                    capabilities=capabilities,
                    context_length=context_length,
                    cost_per_token=0,  # Local models are free
                    free_tier=True,
                    description=f"Local Ollama model ({model_size / 1e9:.1f}GB)"
                )
                models.append(model)

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.config.base_url}")
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")

        # Return default model if no models found
        if not models:
            models = [
                ModelInfo(
                    id="llama2",
                    name="Llama 2",
                    provider="ollama",
                    capabilities=self.config.capabilities or [],
                    context_length=4096,
                    cost_per_token=0,
                    free_tier=True,
                    description="Default Llama 2 model"
                )
            ]

        return models

    def check_availability(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=2
            )
            return response.status_code == 200
        except Exception:
            return False

    def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from the Ollama registry.

        Args:
            model_name: Name of the model to pull

        Returns:
            True if successful
        """
        try:
            data = {"name": model_name, "stream": False}

            response = requests.post(
                f"{self.config.base_url}/api/pull",
                json=data,
                timeout=600  # 10 minutes for large models
            )
            response.raise_for_status()

            logger.info(f"Successfully pulled model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model from Ollama.

        Args:
            model_name: Name of the model to delete

        Returns:
            True if successful
        """
        try:
            data = {"name": model_name}

            response = requests.delete(
                f"{self.config.base_url}/api/delete",
                json=data,
                timeout=30
            )
            response.raise_for_status()

            logger.info(f"Successfully deleted model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            return False

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a model.

        Args:
            model_name: Name of the model

        Returns:
            Model information or None
        """
        try:
            data = {"name": model_name}

            response = requests.post(
                f"{self.config.base_url}/api/show",
                json=data,
                timeout=10
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            return None