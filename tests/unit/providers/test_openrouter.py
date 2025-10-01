"""Tests for OpenRouter provider."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fazztv.providers.openrouter import OpenRouterProvider
from fazztv.providers.base import (
    ModelInfo,
    ModelCapability,
    ProviderConfig
)


@pytest.fixture
def provider_config():
    """Create a test provider configuration."""
    return ProviderConfig(
        provider_id="openrouter",
        api_key="test-api-key",
        endpoint="https://openrouter.ai/api/v1",
        model_aliases={"default": "gpt-3.5-turbo"}
    )


@pytest.fixture
def openrouter_provider(provider_config):
    """Create an OpenRouterProvider instance for testing."""
    return OpenRouterProvider(provider_config)


class TestOpenRouterProvider:
    """Test suite for OpenRouterProvider."""

    def test_initialization(self, provider_config):
        """Test provider initialization with config."""
        provider = OpenRouterProvider(provider_config)
        assert provider.config == provider_config
        assert provider.provider_id == "openrouter"

    def test_initialization_without_config(self):
        """Test provider initialization without config."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "env-api-key"}):
            provider = OpenRouterProvider()
            assert provider.config.api_key == "env-api-key"
            assert provider.provider_id == "openrouter"

    @patch("requests.post")
    def test_query_success(self, mock_post, openrouter_provider):
        """Test successful query to OpenRouter API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response

        result = openrouter_provider.query("Test prompt")

        assert result == "Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Test prompt" in str(call_args)

    @patch("requests.post")
    def test_query_with_model(self, mock_post, openrouter_provider):
        """Test query with specific model."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Model response"}}]
        }
        mock_post.return_value = mock_response

        result = openrouter_provider.query("Test", model="gpt-4")

        assert result == "Model response"
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["model"] == "gpt-4"

    @patch("requests.post")
    def test_query_api_error(self, mock_post, openrouter_provider):
        """Test query handling API errors."""
        mock_post.side_effect = Exception("API Error")

        result = openrouter_provider.query("Test prompt")

        assert result is None

    @patch("requests.get")
    def test_list_models_success(self, mock_get, openrouter_provider):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "gpt-3.5-turbo",
                    "pricing": {"prompt": 0.001, "completion": 0.002},
                    "context_length": 4096
                },
                {
                    "id": "gpt-4",
                    "pricing": {"prompt": 0.01, "completion": 0.03},
                    "context_length": 8192
                }
            ]
        }
        mock_get.return_value = mock_response

        models = openrouter_provider.list_models()

        assert len(models) == 2
        assert models[0].model_id == "gpt-3.5-turbo"
        assert models[1].model_id == "gpt-4"
        assert ModelCapability.CHAT in models[0].capabilities

    @patch("requests.get")
    def test_list_models_api_error(self, mock_get, openrouter_provider):
        """Test model listing with API error."""
        mock_get.side_effect = Exception("API Error")

        models = openrouter_provider.list_models()

        # Should return default models on error
        assert len(models) > 0
        assert all(isinstance(m, ModelInfo) for m in models)

    @patch("requests.get")
    def test_check_availability(self, mock_get, openrouter_provider):
        """Test availability check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "operational"}
        mock_get.return_value = mock_response

        is_available = openrouter_provider.check_availability()

        assert is_available is True

    @patch("requests.get")
    def test_check_availability_failure(self, mock_get, openrouter_provider):
        """Test availability check with failure."""
        mock_get.side_effect = Exception("Connection Error")

        is_available = openrouter_provider.check_availability()

        assert is_available is False

    @patch("requests.post")
    def test_chat_completion(self, mock_post, openrouter_provider):
        """Test chat completion with messages."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Chat response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        mock_post.return_value = mock_response

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]

        response = openrouter_provider.chat(messages)

        assert response is not None
        assert "Chat response" in str(response)

    @patch("requests.post")
    def test_chat_with_streaming(self, mock_post, openrouter_provider):
        """Test chat completion with streaming."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            b'data: {"choices":[{"delta":{"content":" world"}}]}',
            b'data: [DONE]'
        ]
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]

        response = openrouter_provider.chat(messages, stream=True)

        # For streaming, response might be a generator or accumulated response
        assert response is not None


    @patch("requests.post")
    def test_retry_on_rate_limit(self, mock_post, openrouter_provider):
        """Test retry logic on rate limit errors."""
        # First call fails with rate limit
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.json.return_value = {"error": "Rate limit exceeded"}

        # Second call succeeds
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success after retry"}}]
        }

        mock_post.side_effect = [rate_limit_response, success_response]

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = openrouter_provider.query("Test")

        assert result == "Success after retry"
        assert mock_post.call_count == 2


    @patch("requests.post")
    def test_handle_malformed_response(self, mock_post, openrouter_provider):
        """Test handling of malformed API responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "format"}
        mock_post.return_value = mock_response

        result = openrouter_provider.query("Test")

        # Should handle gracefully and return None
        assert result is None