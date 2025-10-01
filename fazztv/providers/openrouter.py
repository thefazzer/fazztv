"""OpenRouter provider implementation."""

import os
import requests
import time
from typing import Optional, List, Dict
from loguru import logger

from .base import BaseProvider, ProviderConfig, ModelCapability, ModelInfo


class OpenRouterProvider(BaseProvider):
    """Provider for OpenRouter API."""

    def __init__(self, config: Optional[ProviderConfig] = None):
        """Initialize OpenRouter provider."""
        if config is None:
            # Create config from environment
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable not set")

            config = ProviderConfig(
                provider_id="openrouter",
                api_key=api_key,
                endpoint="https://openrouter.ai/api/v1",
                default_model="cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TRANSLATION,
                    ModelCapability.SUMMARIZATION
                ]
            )

        # Set defaults if not provided
        if not config.endpoint and not config.base_url:
            config.endpoint = "https://openrouter.ai/api/v1"
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

        # Retry logic for rate limiting
        max_retries = self.config.max_retries
        for attempt in range(max_retries + 1):
            try:
                endpoint = self.config.endpoint or self.config.base_url
                response = requests.post(
                    f"{endpoint}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=self.config.timeout
                )

                if response.status_code == 429:  # Rate limit
                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Rate limit exceeded, max retries reached")
                        return None

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

        return None

    def list_models(self) -> List[ModelInfo]:
        """List available models from OpenRouter."""
        models = []

        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            endpoint = self.config.endpoint or self.config.base_url
            response = requests.get(
                f"{endpoint}/models",
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            data = response.json()

            for model_data in data.get("data", []):
                model_id = model_data.get("id", "")
                is_free = ":free" in model_id

                model = ModelInfo(
                    model_id=model_id,
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
                    model_id="cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
                    name="Dolphin 3.0 Mistral 24B (Free)",
                    provider="openrouter",
                    capabilities=self.config.capabilities or [],
                    context_length=16384,
                    cost_per_token=0,
                    free_tier=True,
                    description="Free tier Mistral-based model"
                ),
                ModelInfo(
                    model_id="meta-llama/llama-3.2-3b-instruct:free",
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

            endpoint = self.config.endpoint or self.config.base_url
            response = requests.get(
                f"{endpoint}/models",
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
            endpoint = self.config.endpoint or self.config.base_url
            response = requests.post(
                f"{endpoint}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.config.timeout,
                stream=kwargs.get('stream', False)
            )
            response.raise_for_status()

            if kwargs.get('stream', False):
                # Handle streaming response
                accumulated_content = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                import json
                                stream_data = json.loads(data_str)
                                if 'choices' in stream_data and stream_data['choices']:
                                    delta = stream_data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        accumulated_content += content
                            except json.JSONDecodeError:
                                continue
                return accumulated_content if accumulated_content else None
            else:
                result = response.json()
                if "choices" in result and result["choices"]:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    if content:
                        return content

        except Exception as e:
            logger.error(f"OpenRouter chat request failed: {e}")

        return None