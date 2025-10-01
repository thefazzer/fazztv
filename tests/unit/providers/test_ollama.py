"""Tests for Ollama provider."""
import pytest
from unittest.mock import Mock, patch
from fazztv.providers.ollama import OllamaProvider
from fazztv.providers.base import ProviderConfig
from fazztv.exceptions import APIError as ProviderError


class TestOllamaProvider:
    """Test suite for Ollama provider."""

    @pytest.fixture
    def provider(self):
        """Create an Ollama provider instance."""
        config = ProviderConfig(provider_id="ollama")
        return OllamaProvider(config)

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.config.name == "ollama"
        assert provider.config.base_url == "http://localhost:11434"
        assert provider.config.default_model == "llama2"

    def test_initialization_with_custom_config(self):
        """Test provider initialization with custom configuration."""
        config = ProviderConfig(
            provider_id="ollama",
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
        # Verify the call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        json_data = call_args[1]['json']
        assert json_data['model'] == "llama2"
        assert json_data['prompt'] == "Test prompt"
        assert json_data['stream'] is False
        assert 'timeout' in call_args[1]

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

        # Check that the request was made with correct URL and timeout
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]['timeout'] == 60

        # Check that essential parameters are in JSON
        json_data = call_args[1]['json']
        assert json_data['model'] == "llama2"
        assert json_data['prompt'] == "Test"
        assert json_data['stream'] is False

    @patch('requests.post')
    def test_query_http_error(self, mock_post, provider):
        """Test query with HTTP error."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error: Internal Server Error")
        mock_response.raise_for_status.side_effect.response = mock_response
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

            assert provider.check_availability() is True
            mock_get.assert_called_once_with(
                "http://localhost:11434/api/tags",
                timeout=2
            )

    def test_is_available_false(self, provider):
        """Test availability check when service is down."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError()

            assert provider.check_availability() is False

    def test_get_models(self, provider):
        """Test getting available models."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama2", "size": 3800000000},
                    {"name": "mistral", "size": 4100000000},
                    {"name": "codellama", "size": 3700000000}
                ]
            }
            mock_get.return_value = mock_response

            models = provider.list_models()

            assert len(models) == 3
            model_ids = [m.id for m in models]
            assert "llama2" in model_ids
            assert "mistral" in model_ids
            assert "codellama" in model_ids

    def test_get_models_error(self, provider):
        """Test getting models with error."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError()

            models = provider.list_models()
            # Provider returns default model on error
            assert len(models) >= 1