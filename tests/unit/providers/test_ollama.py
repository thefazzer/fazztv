"""Tests for Ollama provider."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fazztv.providers.ollama import OllamaProvider
from fazztv.providers.base import ProviderConfig
from fazztv.exceptions import APIError as ProviderError


class TestOllamaProvider:
    """Test suite for Ollama provider."""

    @pytest.fixture
    def provider(self):
        """Create an Ollama provider instance."""
        config = ProviderConfig(name="ollama")
        return OllamaProvider(config)

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.config.name == "ollama"
        assert provider.config.base_url == "http://localhost:11434"
        assert provider.config.default_model == "llama2"

    def test_initialization_with_custom_config(self):
        """Test provider initialization with custom configuration."""
        config = ProviderConfig(
            name="ollama",
            base_url="http://custom:8080",
            default_model="mistral"
        )
        provider = OllamaProvider(config)
        assert provider.config.base_url == "http://custom:8080"
        assert provider.config.default_model == "mistral"

    @patch('requests.post')
    def test_query_success(self, mock_post, provider):
        """Test successful query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Test response from Ollama"
        }
        mock_post.return_value = mock_response

        result = provider.query("Test prompt")

        assert result == "Test response from Ollama"
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",
                "prompt": "Test prompt",
                "stream": False
            },
            timeout=30
        )

    @patch('requests.post')
    def test_query_with_timeout(self, mock_post, provider):
        """Test query with custom timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Response"
        }
        mock_post.return_value = mock_response

        provider.query("Test", timeout=60)

        mock_post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",
                "prompt": "Test",
                "stream": False
            },
            timeout=60
        )

    @patch('requests.post')
    def test_query_http_error(self, mock_post, provider):
        """Test query with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "HTTP 500" in str(exc_info.value)

    @patch('requests.post')
    def test_query_connection_error(self, mock_post, provider):
        """Test query with connection error."""
        mock_post.side_effect = ConnectionError("Connection refused")

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Connection error" in str(exc_info.value)

    @patch('requests.post')
    def test_query_timeout_error(self, mock_post, provider):
        """Test query with timeout error."""
        import requests
        mock_post.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Request timeout" in str(exc_info.value)

    @patch('requests.post')
    def test_query_invalid_json_response(self, mock_post, provider):
        """Test query with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Invalid response format" in str(exc_info.value)

    @patch('requests.post')
    def test_query_missing_response_field(self, mock_post, provider):
        """Test query with missing response field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Some error"}
        mock_post.return_value = mock_response

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Missing response field" in str(exc_info.value)

    def test_is_available(self, provider):
        """Test availability check."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert provider.is_available() is True
            mock_get.assert_called_once_with(
                "http://localhost:11434/api/tags",
                timeout=5
            )

    def test_is_available_false(self, provider):
        """Test availability check when service is down."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError()

            assert provider.is_available() is False

    def test_get_models(self, provider):
        """Test getting available models."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama2"},
                    {"name": "mistral"},
                    {"name": "codellama"}
                ]
            }
            mock_get.return_value = mock_response

            models = provider.get_models()

            assert len(models) == 3
            assert "llama2" in models
            assert "mistral" in models
            assert "codellama" in models

    def test_get_models_error(self, provider):
        """Test getting models with error."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError()

            models = provider.get_models()
            assert models == []