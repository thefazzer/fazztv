"""Tests for provider configuration management."""

import json
import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open, MagicMock
import yaml

from fazztv.providers.config import ProviderConfigLoader
from fazztv.providers.base import ProviderConfig, ModelCapability


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_provider_config():
    """Create a sample provider configuration."""
    return ProviderConfig(
        provider_id="test_provider",
        api_key="test_key_123",
        endpoint="https://api.test.com/v1",
        model_aliases={"default": "test-model-v1"},
        default_model="test-model-v1",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def sample_config_dict():
    """Create a sample configuration dictionary."""
    return {
        "providers": {
            "openai": {
                "api_key": "openai_key",
                "endpoint": "https://api.openai.com/v1",
                "default_model": "gpt-3.5-turbo"
            },
            "anthropic": {
                "api_key": "anthropic_key",
                "endpoint": "https://api.anthropic.com",
                "default_model": "claude-3-opus"
            }
        },
        "default_provider": "openai"
    }


class TestProviderConfig:
    """Test suite for ProviderConfig class."""

    def test_provider_config_creation(self):
        """Test creating a provider configuration."""
        config = ProviderConfig(
            provider_id="test",
            api_key="key123",
            endpoint="https://api.test.com"
        )

        assert config.provider_id == "test"
        assert config.api_key == "key123"
        assert config.endpoint == "https://api.test.com"
        assert config.timeout == 60  # default value
        assert config.max_retries == 3  # default value

    def test_provider_config_with_all_fields(self, sample_provider_config):
        """Test provider config with all fields set."""
        assert sample_provider_config.provider_id == "test_provider"
        assert sample_provider_config.api_key == "test_key_123"
        assert sample_provider_config.timeout == 30
        assert sample_provider_config.model_aliases["default"] == "test-model-v1"


class TestProviderConfigLoader:
    """Test suite for ProviderConfigLoader."""

    def test_initialization(self):
        """Test config manager initialization."""
        manager = ProviderConfigLoader()
        assert manager.configs == {}
        assert manager.default_provider is None

    def test_load_from_env_variables(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "env_openai_key",
            "ANTHROPIC_API_KEY": "env_anthropic_key",
            "OPENROUTER_API_KEY": "env_openrouter_key",
            "GROQ_API_KEY": "env_groq_key",
            "DEFAULT_PROVIDER": "openai"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            manager = ProviderConfigLoader()
            manager.load_from_env()

            assert "openai" in manager.configs
            assert manager.configs["openai"].api_key == "env_openai_key"
            assert "anthropic" in manager.configs
            assert manager.configs["anthropic"].api_key == "env_anthropic_key"
            assert manager.default_provider == "openai"

    def test_load_from_yaml_file(self, temp_config_dir, sample_config_dict):
        """Test loading configuration from YAML file."""
        config_file = temp_config_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_dict, f)

        manager = ProviderConfigLoader()
        manager.load_from_file(str(config_file))

        assert "openai" in manager.configs
        assert manager.configs["openai"].api_key == "openai_key"
        assert "anthropic" in manager.configs
        assert manager.default_provider == "openai"

    def test_load_from_json_file(self, temp_config_dir, sample_config_dict):
        """Test loading configuration from JSON file."""
        config_file = temp_config_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(sample_config_dict, f)

        manager = ProviderConfigLoader()
        manager.load_from_file(str(config_file))

        assert "openai" in manager.configs
        assert manager.configs["openai"].api_key == "openai_key"

    def test_load_from_dict(self, sample_config_dict):
        """Test loading configuration from dictionary."""
        manager = ProviderConfigLoader()
        manager.load_from_dict(sample_config_dict)

        assert len(manager.configs) == 2
        assert "openai" in manager.configs
        assert "anthropic" in manager.configs
        assert manager.default_provider == "openai"

    def test_add_provider_config(self, sample_provider_config):
        """Test adding a provider configuration."""
        manager = ProviderConfigLoader()
        manager.add_provider(sample_provider_config)

        assert "test_provider" in manager.configs
        assert manager.configs["test_provider"] == sample_provider_config

    def test_get_provider_config(self, sample_provider_config):
        """Test getting a provider configuration."""
        manager = ProviderConfigLoader()
        manager.add_provider(sample_provider_config)

        config = manager.get_provider("test_provider")
        assert config == sample_provider_config

        # Test non-existent provider
        assert manager.get_provider("non_existent") is None

    def test_remove_provider_config(self, sample_provider_config):
        """Test removing a provider configuration."""
        manager = ProviderConfigLoader()
        manager.add_provider(sample_provider_config)

        assert "test_provider" in manager.configs
        manager.remove_provider("test_provider")
        assert "test_provider" not in manager.configs

    def test_list_providers(self, sample_config_dict):
        """Test listing all provider IDs."""
        manager = ProviderConfigLoader()
        manager.load_from_dict(sample_config_dict)

        providers = manager.list_providers()
        assert len(providers) == 2
        assert "openai" in providers
        assert "anthropic" in providers

    def test_validate_provider_config(self):
        """Test provider configuration validation."""
        manager = ProviderConfigLoader()

        # Valid config
        valid_config = ProviderConfig(
            provider_id="test",
            api_key="key123",
            endpoint="https://api.test.com"
        )
        assert manager.validate_config(valid_config) is True

        # Invalid config - missing API key
        invalid_config = ProviderConfig(
            provider_id="test",
            api_key="",
            endpoint="https://api.test.com"
        )
        assert manager.validate_config(invalid_config) is False

    def test_load_provider_with_defaults(self):
        """Test loading provider with default values."""
        config_data = {
            "provider_id": "test",
            "api_key": "test_key"
            # endpoint and other fields should use defaults
        }

        manager = ProviderConfigLoader()
        config = manager._load_provider("test", config_data)

        assert config.provider_id == "test"
        assert config.api_key == "test_key"
        assert config.endpoint is not None  # Should have default
        assert config.timeout == 60  # Default value

    def test_merge_configurations(self):
        """Test merging configurations from multiple sources."""
        manager = ProviderConfigLoader()

        # Load from dict first
        dict_config = {
            "providers": {
                "openai": {
                    "api_key": "dict_key",
                    "default_model": "gpt-3.5-turbo"
                }
            }
        }
        manager.load_from_dict(dict_config)

        # Override with env var
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env_key"}):
            manager.load_from_env()

        # Env var should override dict config
        assert manager.configs["openai"].api_key == "env_key"

    def test_export_to_dict(self, sample_provider_config):
        """Test exporting configuration to dictionary."""
        manager = ProviderConfigLoader()
        manager.add_provider(sample_provider_config)
        manager.default_provider = "test_provider"

        exported = manager.export_to_dict()

        assert "providers" in exported
        assert "test_provider" in exported["providers"]
        assert exported["default_provider"] == "test_provider"

    def test_save_to_file(self, temp_config_dir, sample_provider_config):
        """Test saving configuration to file."""
        manager = ProviderConfigLoader()
        manager.add_provider(sample_provider_config)

        # Save to YAML
        yaml_file = temp_config_dir / "saved_config.yaml"
        manager.save_to_file(str(yaml_file))
        assert yaml_file.exists()

        # Save to JSON
        json_file = temp_config_dir / "saved_config.json"
        manager.save_to_file(str(json_file))
        assert json_file.exists()

    def test_get_default_provider(self, sample_config_dict):
        """Test getting the default provider."""
        manager = ProviderConfigLoader()
        manager.load_from_dict(sample_config_dict)

        default = manager.get_default_provider()
        assert default is not None
        assert default.provider_id == "openai"

    def test_set_default_provider(self, sample_config_dict):
        """Test setting the default provider."""
        manager = ProviderConfigLoader()
        manager.load_from_dict(sample_config_dict)

        manager.set_default_provider("anthropic")
        assert manager.default_provider == "anthropic"

        # Test setting non-existent provider
        with pytest.raises(ValueError):
            manager.set_default_provider("non_existent")


