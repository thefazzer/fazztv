"""Configuration loader for multi-provider system."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from fazztv.config import get_settings
from .base import ProviderConfig, ModelCapability
from .registry import ProviderRegistry
from .manager import ProviderManager
from .openrouter import OpenRouterProvider
from .openai import OpenAIProvider
from .ollama import OllamaProvider


class ProviderConfigLoader:
    """Load and configure providers from settings."""

    PROVIDER_CLASSES = {
        "openrouter": OpenRouterProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the config loader.

        Args:
            config_file: Path to provider configuration file (JSON or YAML)
        """
        self.config_file = config_file
        self.settings = get_settings()
        self.registry = ProviderRegistry()
        self.manager = ProviderManager(self.registry)

        # Register provider classes
        for name, cls in self.PROVIDER_CLASSES.items():
            self.registry.register_provider_class(name, cls)

    def load_from_env(self) -> ProviderManager:
        """
        Load providers from environment variables.

        Returns:
            Configured ProviderManager
        """
        # Load OpenRouter if configured
        if self.settings.openrouter_api_key:
            config = ProviderConfig(
                name="openrouter",
                api_key=self.settings.openrouter_api_key,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TRANSLATION,
                    ModelCapability.SUMMARIZATION
                ]
            )
            self.registry.add_provider(config)
            logger.info("Loaded OpenRouter provider from environment")

        # Load OpenAI if configured
        if self.settings.openai_api_key:
            config = ProviderConfig(
                name="openai",
                api_key=self.settings.openai_api_key,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TRANSLATION,
                    ModelCapability.SUMMARIZATION,
                    ModelCapability.EMBEDDING,
                    ModelCapability.MODERATION
                ]
            )
            self.registry.add_provider(config)
            logger.info("Loaded OpenAI provider from environment")

        # Always try to load Ollama (local)
        ollama_config = ProviderConfig(
            name="ollama",
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434")
        )
        self.registry.add_provider(ollama_config)
        logger.info("Loaded Ollama provider")

        return self.manager

    def load_from_file(self, file_path: Optional[str] = None) -> ProviderManager:
        """
        Load providers from configuration file.

        Args:
            file_path: Path to configuration file

        Returns:
            Configured ProviderManager
        """
        file_path = file_path or self.config_file
        if not file_path:
            logger.warning("No configuration file specified")
            return self.load_from_env()

        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            return self.load_from_env()

        try:
            with open(path) as f:
                if path.suffix == ".json":
                    config_data = json.load(f)
                elif path.suffix in [".yaml", ".yml"]:
                    import yaml
                    config_data = yaml.safe_load(f)
                else:
                    logger.error(f"Unsupported config file format: {path.suffix}")
                    return self.load_from_env()

            # Load providers from config
            providers = config_data.get("providers", [])
            for provider_data in providers:
                self._load_provider(provider_data)

            # Load manager settings
            manager_config = config_data.get("manager", {})
            self.manager.fallback_enabled = manager_config.get("fallback_enabled", True)
            self.manager.load_balancing = manager_config.get("load_balancing", False)

            logger.info(f"Loaded {len(providers)} providers from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}")
            return self.load_from_env()

        return self.manager

    def load_from_dict(self, config: Dict[str, Any]) -> ProviderManager:
        """
        Load providers from dictionary configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Configured ProviderManager
        """
        providers = config.get("providers", [])
        for provider_data in providers:
            self._load_provider(provider_data)

        # Load manager settings
        manager_config = config.get("manager", {})
        self.manager.fallback_enabled = manager_config.get("fallback_enabled", True)
        self.manager.load_balancing = manager_config.get("load_balancing", False)

        return self.manager

    def _load_provider(self, provider_data: Dict[str, Any]) -> None:
        """
        Load a single provider from configuration data.

        Args:
            provider_data: Provider configuration dictionary
        """
        try:
            name = provider_data.get("name")
            if not name:
                logger.error("Provider configuration missing 'name'")
                return

            # Parse capabilities
            capabilities = []
            for cap_str in provider_data.get("capabilities", []):
                try:
                    cap = ModelCapability(cap_str)
                    capabilities.append(cap)
                except ValueError:
                    logger.warning(f"Unknown capability: {cap_str}")

            # Create provider config
            config = ProviderConfig(
                name=name,
                api_key=provider_data.get("api_key") or os.getenv(provider_data.get("api_key_env", "")),
                base_url=provider_data.get("base_url"),
                default_model=provider_data.get("default_model"),
                timeout=provider_data.get("timeout", 30),
                max_retries=provider_data.get("max_retries", 3),
                custom_headers=provider_data.get("headers"),
                capabilities=capabilities
            )

            # Get provider class
            provider_type = provider_data.get("type", name)
            if provider_type in self.PROVIDER_CLASSES:
                provider_class = self.PROVIDER_CLASSES[provider_type]
            else:
                logger.error(f"Unknown provider type: {provider_type}")
                return

            # Add to registry
            self.registry.add_provider(config, provider_class)
            logger.info(f"Loaded provider: {name}")

        except Exception as e:
            logger.error(f"Failed to load provider: {e}")

    @staticmethod
    def create_default_config() -> Dict[str, Any]:
        """
        Create a default configuration template.

        Returns:
            Default configuration dictionary
        """
        return {
            "providers": [
                {
                    "name": "openrouter",
                    "type": "openrouter",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "default_model": "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
                    "capabilities": [
                        "text_generation",
                        "chat",
                        "code_generation",
                        "translation",
                        "summarization"
                    ]
                },
                {
                    "name": "openai",
                    "type": "openai",
                    "api_key_env": "OPENAI_API_KEY",
                    "default_model": "gpt-3.5-turbo",
                    "capabilities": [
                        "text_generation",
                        "chat",
                        "code_generation",
                        "translation",
                        "summarization",
                        "embedding",
                        "moderation"
                    ]
                },
                {
                    "name": "ollama",
                    "type": "ollama",
                    "base_url": "http://localhost:11434",
                    "default_model": "llama2",
                    "capabilities": [
                        "text_generation",
                        "chat",
                        "code_generation"
                    ]
                }
            ],
            "manager": {
                "fallback_enabled": True,
                "load_balancing": False
            }
        }

    def save_default_config(self, file_path: str) -> None:
        """
        Save default configuration to file.

        Args:
            file_path: Path to save configuration
        """
        config = self.create_default_config()
        path = Path(file_path)

        try:
            with open(path, "w") as f:
                if path.suffix == ".json":
                    json.dump(config, f, indent=2)
                elif path.suffix in [".yaml", ".yml"]:
                    import yaml
                    yaml.dump(config, f, default_flow_style=False)
                else:
                    json.dump(config, f, indent=2)

            logger.info(f"Saved default configuration to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")


def get_provider_manager(config_file: Optional[str] = None) -> ProviderManager:
    """
    Get a configured provider manager.

    Args:
        config_file: Optional configuration file path

    Returns:
        Configured ProviderManager
    """
    loader = ProviderConfigLoader(config_file)

    if config_file and Path(config_file).exists():
        return loader.load_from_file(config_file)
    else:
        return loader.load_from_env()