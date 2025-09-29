"""Tests for OpenAI provider."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fazztv.providers.openai import OpenAIProvider
from fazztv.providers.base import ProviderConfig
from fazztv.exceptions import APIError as ProviderError


class TestOpenAIProvider:
    """Test suite for OpenAI provider."""

    @pytest.fixture
    def provider(self):
        """Create an OpenAI provider instance."""
        config = ProviderConfig(name="openai", api_key="test_key")
        return OpenAIProvider(config)

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.config.name == "openai"
        assert provider.config.api_key == "test_key"
        assert provider.config.default_model == "gpt-3.5-turbo"
        assert provider.config.base_url == "https://api.openai.com/v1"

    def test_initialization_without_api_key(self):
        """Test provider initialization without API key."""
        config = ProviderConfig(name="openai")  # No API key provided
        with pytest.raises(ValueError) as exc_info:
            # The validation should occur during provider initialization
            provider = OpenAIProvider(config)
            provider.query("test")  # This should fail
        # Note: Actual behavior depends on implementation

    def test_initialization_with_custom_config(self):
        """Test provider initialization with custom configuration."""
        config = ProviderConfig(
            name="openai",
            api_key="test_key",
            default_model="gpt-4",
            base_url="https://api.openai.com/v1"
        )
        provider = OpenAIProvider(config)
        assert provider.config.default_model == "gpt-4"
        assert provider.config.api_key == "test_key"

    @patch('openai.ChatCompletion.create')
    def test_query_success(self, mock_create, provider):
        """Test successful query."""
        mock_create.return_value = {
            "choices": [{
                "message": {
                    "content": "Test response from OpenAI"
                }
            }]
        }

        result = provider.query("Test prompt")

        assert result == "Test response from OpenAI"
        mock_create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Test prompt"}
            ],
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )

    @patch('openai.ChatCompletion.create')
    def test_query_with_system_message(self, mock_create, provider):
        """Test query with system message."""
        mock_create.return_value = {
            "choices": [{
                "message": {
                    "content": "Response"
                }
            }]
        }

        provider.system_message = "You are a helpful assistant."
        result = provider.query("Test")

        mock_create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Test"}
            ],
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )

    @patch('openai.ChatCompletion.create')
    def test_query_with_conversation_history(self, mock_create, provider):
        """Test query with conversation history."""
        mock_create.return_value = {
            "choices": [{
                "message": {
                    "content": "Response"
                }
            }]
        }

        provider.conversation_history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
        result = provider.query("New question")

        expected_messages = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
            {"role": "user", "content": "New question"}
        ]
        mock_create.assert_called_once()
        actual_messages = mock_create.call_args[1]['messages']
        assert actual_messages == expected_messages

    @patch('openai.ChatCompletion.create')
    def test_query_rate_limit_error(self, mock_create, provider):
        """Test query with rate limit error."""
        import openai
        mock_create.side_effect = openai.error.RateLimitError("Rate limit exceeded")

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Rate limit exceeded" in str(exc_info.value)

    @patch('openai.ChatCompletion.create')
    def test_query_api_error(self, mock_create, provider):
        """Test query with API error."""
        import openai
        mock_create.side_effect = openai.error.APIError("API Error")

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "API error" in str(exc_info.value)

    @patch('openai.ChatCompletion.create')
    def test_query_authentication_error(self, mock_create, provider):
        """Test query with authentication error."""
        import openai
        mock_create.side_effect = openai.error.AuthenticationError("Invalid API key")

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Authentication failed" in str(exc_info.value)

    @patch('openai.ChatCompletion.create')
    def test_query_timeout_error(self, mock_create, provider):
        """Test query with timeout error."""
        import openai
        mock_create.side_effect = openai.error.Timeout("Request timed out")

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Request timeout" in str(exc_info.value)

    @patch('openai.ChatCompletion.create')
    def test_query_empty_response(self, mock_create, provider):
        """Test query with empty response."""
        mock_create.return_value = {
            "choices": []
        }

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "No response" in str(exc_info.value)

    @patch('openai.ChatCompletion.create')
    def test_query_malformed_response(self, mock_create, provider):
        """Test query with malformed response."""
        mock_create.return_value = {
            "choices": [{
                "text": "Wrong format"
            }]
        }

        with pytest.raises(ProviderError) as exc_info:
            provider.query("Test prompt")

        assert "Invalid response format" in str(exc_info.value)

    @patch('openai.Model.list')
    def test_is_available(self, mock_list, provider):
        """Test availability check."""
        mock_list.return_value = {"data": [{"id": "gpt-3.5-turbo"}]}

        assert provider.is_available() is True
        mock_list.assert_called_once()

    @patch('openai.Model.list')
    def test_is_available_false(self, mock_list, provider):
        """Test availability check when service is down."""
        import openai
        mock_list.side_effect = openai.error.APIConnectionError("Connection failed")

        assert provider.is_available() is False

    @patch('openai.Model.list')
    def test_get_models(self, mock_list, provider):
        """Test getting available models."""
        mock_list.return_value = {
            "data": [
                {"id": "gpt-3.5-turbo"},
                {"id": "gpt-4"},
                {"id": "text-davinci-003"}
            ]
        }

        models = provider.get_models()

        assert len(models) == 3
        assert "gpt-3.5-turbo" in models
        assert "gpt-4" in models
        assert "text-davinci-003" in models

    def test_clear_conversation(self, provider):
        """Test clearing conversation history."""
        provider.conversation_history = [
            {"role": "user", "content": "Test"},
            {"role": "assistant", "content": "Response"}
        ]

        provider.clear_conversation()

        assert provider.conversation_history == []

    def test_set_system_message(self, provider):
        """Test setting system message."""
        provider.set_system_message("New system message")
        assert provider.system_message == "New system message"