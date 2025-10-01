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
        self.configs: Dict[str, ProviderConfig] = {}
        self.default_provider: Optional[str] = None

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
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            config = ProviderConfig(
                provider_id="openrouter",
                api_key=openrouter_key,
                endpoint="https://openrouter.ai/api/v1",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TRANSLATION,
                    ModelCapability.SUMMARIZATION
                ]
            )
            self.configs["openrouter"] = config
            self.registry.add_provider(config)
            logger.info("Loaded OpenRouter provider from environment")

        # Load OpenAI if configured
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            config = ProviderConfig(
                provider_id="openai",
                api_key=openai_key,
                endpoint="https://api.openai.com/v1",
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
            self.configs["openai"] = config
            self.registry.add_provider(config)
            logger.info("Loaded OpenAI provider from environment")

        # Load Anthropic if configured
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            config = ProviderConfig(
                provider_id="anthropic",
                api_key=anthropic_key,
                endpoint="https://api.anthropic.com",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TRANSLATION,
                    ModelCapability.SUMMARIZATION
                ]
            )
            self.configs["anthropic"] = config
            # Don't add to registry since we don't have the provider class
            logger.info("Loaded Anthropic provider from environment")

        # Load Groq if configured
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            config = ProviderConfig(
                provider_id="groq",
                api_key=groq_key,
                endpoint="https://api.groq.com/openai/v1",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHAT,
                    ModelCapability.CODE_GENERATION
                ]
            )
            self.configs["groq"] = config
            # Don't add to registry since we don't have the provider class
            logger.info("Loaded Groq provider from environment")

        # Always try to load Ollama (local)
        ollama_config = ProviderConfig(
            provider_id="ollama",
            endpoint=os.getenv("OLLAMA_URL", "http://localhost:11434")
        )
        self.configs["ollama"] = ollama_config
        self.registry.add_provider(ollama_config)
        logger.info("Loaded Ollama provider")

        # Set default provider
        default_provider = os.getenv("DEFAULT_PROVIDER")
        if default_provider and default_provider in self.configs:
            self.default_provider = default_provider

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
                if isinstance(provider_data, dict) and "name" in provider_data:
                    # Old format with _load_provider method
                    self._load_provider_legacy(provider_data)
                else:
                    # New format - handle as dict
                    self.load_from_dict(config_data)
                    break

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
        providers = config.get("providers", {})

        # Handle both list and dict formats
        if isinstance(providers, dict):
            # Dict format: {"openai": {"api_key": "...", ...}, ...}
            for provider_id, provider_data in providers.items():
                if isinstance(provider_data, dict):
                    provider_data["provider_id"] = provider_id
                    self._load_provider_from_dict(provider_data)

        elif isinstance(providers, list):
            # List format: [{"name": "openai", "api_key": "...", ...}, ...]
            for provider_data in providers:
                self._load_provider(provider_data)

        # Set default provider
        if "default_provider" in config:
            self.default_provider = config["default_provider"]

        # Load manager settings
        manager_config = config.get("manager", {})
        if hasattr(self.manager, 'fallback_enabled'):
            self.manager.fallback_enabled = manager_config.get("fallback_enabled", True)
        if hasattr(self.manager, 'load_balancing'):
            self.manager.load_balancing = manager_config.get("load_balancing", False)

        return self.manager

    def _load_provider_legacy(self, provider_data: Dict[str, Any]) -> None:
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

    def _load_provider_from_dict(self, provider_data: Dict[str, Any]) -> None:
        """
        Load a single provider from dictionary configuration data.

        Args:
            provider_data: Provider configuration dictionary
        """
        try:
            provider_id = provider_data.get("provider_id")
            if not provider_id:
                logger.error("Provider configuration missing 'provider_id'")
                return

            # Create provider config
            config = ProviderConfig(
                provider_id=provider_id,
                api_key=provider_data.get("api_key"),
                endpoint=provider_data.get("endpoint"),
                default_model=provider_data.get("default_model"),
                timeout=provider_data.get("timeout", 60),
                max_retries=provider_data.get("max_retries", 3),
                model_aliases=provider_data.get("model_aliases", {}),
                custom_headers=provider_data.get("headers"),
                capabilities=[]
            )

            # Add to configs
            self.configs[provider_id] = config
            logger.info(f"Loaded provider: {provider_id}")

        except Exception as e:
            logger.error(f"Failed to load provider from dict: {e}")

    def add_provider(self, config: ProviderConfig) -> None:
        """
        Add a provider configuration.

        Args:
            config: Provider configuration to add
        """
        self.configs[config.provider_id] = config

    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        """
        Get a provider configuration.

        Args:
            provider_id: Provider ID to get

        Returns:
            Provider configuration or None
        """
        return self.configs.get(provider_id)

    def remove_provider(self, provider_id: str) -> None:
        """
        Remove a provider configuration.

        Args:
            provider_id: Provider ID to remove
        """
        if provider_id in self.configs:
            del self.configs[provider_id]

    def list_providers(self) -> List[str]:
        """
        List all provider IDs.

        Returns:
            List of provider IDs
        """
        return list(self.configs.keys())

    def validate_config(self, config: ProviderConfig) -> bool:
        """
        Validate a provider configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid
        """
        return config.validate() and bool(config.api_key)

    def _load_provider(self, provider_id: str, provider_data: Dict[str, Any]) -> ProviderConfig:
        """
        Load provider from data with defaults.

        Args:
            provider_id: Provider identifier
            provider_data: Provider configuration data

        Returns:
            ProviderConfig instance
        """
        return ProviderConfig(
            provider_id=provider_id,
            api_key=provider_data.get("api_key", ""),
            endpoint=provider_data.get("endpoint", ""),
            default_model=provider_data.get("default_model"),
            timeout=provider_data.get("timeout", 60),
            max_retries=provider_data.get("max_retries", 3),
            model_aliases=provider_data.get("model_aliases", {}),
            capabilities=[]
        )

    def export_to_dict(self) -> Dict[str, Any]:
        """
        Export configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        providers = {}
        for provider_id, config in self.configs.items():
            providers[provider_id] = {
                "api_key": config.api_key,
                "endpoint": config.endpoint,
                "default_model": config.default_model,
                "timeout": config.timeout,
                "max_retries": config.max_retries,
                "model_aliases": config.model_aliases
            }

        result = {
            "providers": providers
        }

        if self.default_provider:
            result["default_provider"] = self.default_provider

        return result

    def save_to_file(self, file_path: str) -> None:
        """
        Save configuration to file.

        Args:
            file_path: Path to save configuration
        """
        config_dict = self.export_to_dict()
        path = Path(file_path)

        try:
            with open(path, "w") as f:
                if path.suffix == ".json":
                    json.dump(config_dict, f, indent=2)
                elif path.suffix in [".yaml", ".yml"]:
                    import yaml
                    yaml.dump(config_dict, f, default_flow_style=False)
                else:
                    json.dump(config_dict, f, indent=2)

            logger.info(f"Saved configuration to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def get_default_provider(self) -> Optional[ProviderConfig]:
        """
        Get the default provider configuration.

        Returns:
            Default provider configuration or None
        """
        if self.default_provider and self.default_provider in self.configs:
            return self.configs[self.default_provider]
        return None

    def set_default_provider(self, provider_id: str) -> None:
        """
        Set the default provider.

        Args:
            provider_id: Provider ID to set as default

        Raises:
            ValueError: If provider doesn't exist
        """
        if provider_id not in self.configs:
            raise ValueError(f"Provider '{provider_id}' not found")
        self.default_provider = provider_id

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