# Multi-Provider System Documentation

## Overview

The FazzTV Multi-Provider System enables seamless integration and management of multiple AI model providers, offering automatic fallback, load balancing, and unified API access across different providers.

## Architecture

### Core Components

1. **BaseProvider**: Abstract base class defining the provider interface
2. **ProviderRegistry**: Central registry for managing provider instances
3. **ProviderManager**: Orchestrates operations across multiple providers
4. **ProviderConfigLoader**: Handles configuration loading and initialization

### Supported Providers

- **OpenRouter**: Access to various open-source and commercial models
- **OpenAI**: GPT models and OpenAI services
- **Ollama**: Local model hosting and inference

## Features

### 1. Automatic Fallback
Automatically switches to alternative providers when the primary provider fails.

```python
from fazztv.providers import get_provider_manager

manager = get_provider_manager()
response = manager.query_with_fallback(
    "Your prompt here",
    preferred_provider="openrouter"
)
```

### 2. Load Balancing
Distribute requests across providers to optimize performance and avoid rate limits.

```python
manager.enable_load_balancing(True)
# Requests will be distributed across available providers
```

### 3. Capability-Based Selection
Find providers based on specific capabilities.

```python
from fazztv.providers import ModelCapability

# Find providers that support code generation
provider = manager.find_best_provider(ModelCapability.CODE_GENERATION)
```

### 4. Cost Optimization
Automatically select the most cost-effective models.

```python
# Get the cheapest model for text generation
cheapest_model = registry.get_cheapest_model(
    capability=ModelCapability.TEXT_GENERATION,
    free_only=True
)
```

## Configuration

### Environment Variables

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key

# Ollama Configuration (optional)
OLLAMA_URL=http://localhost:11434
```

### Configuration File

Create a `providers.json` file:

```json
{
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
    "fallback_enabled": true,
    "load_balancing": false
  }
}
```

## Usage Examples

### Basic Usage

```python
from fazztv.providers import get_provider_manager

# Initialize manager with default configuration
manager = get_provider_manager()

# Simple query with automatic provider selection
response = manager.query_with_fallback("Explain quantum computing")
print(response)
```

### Chat Conversations

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "What is the capital of France?"}
]

response = manager.chat_with_fallback(messages)
print(response)
```

### Comparing Provider Responses

```python
# Compare responses from multiple providers
responses = manager.compare_responses(
    "What are the benefits of renewable energy?",
    providers=["openrouter", "openai", "ollama"]
)

for provider, response in responses.items():
    print(f"{provider}: {response[:100]}...")
```

### Batch Processing

```python
prompts = [
    "Translate 'Hello' to Spanish",
    "Translate 'Goodbye' to French",
    "Translate 'Thank you' to German"
]

responses = manager.batch_query(prompts, provider="openai")
for prompt, response in zip(prompts, responses):
    print(f"{prompt}: {response}")
```

### Provider-Specific Features

#### OpenAI Embeddings

```python
from fazztv.providers import OpenAIProvider, ProviderConfig

config = ProviderConfig(
    name="openai",
    api_key="your_key"
)
provider = OpenAIProvider(config)

embeddings = provider.get_embeddings("Sample text for embedding")
```

#### OpenAI Content Moderation

```python
result = provider.moderate_content("Content to check for safety")
print(f"Safe: {result['safe']}")
print(f"Concerns: {result['concerns']}")
print(f"Rating: {result['rating']}")
```

#### Ollama Model Management

```python
from fazztv.providers import OllamaProvider, ProviderConfig

config = ProviderConfig(name="ollama")
provider = OllamaProvider(config)

# Pull a new model
provider.pull_model("codellama")

# List available models
models = provider.list_models()
for model in models:
    print(f"{model.name}: {model.description}")

# Delete a model
provider.delete_model("llama2")
```

### Custom Provider Implementation

```python
from fazztv.providers import BaseProvider, ProviderConfig, ModelInfo

class CustomProvider(BaseProvider):
    def query(self, prompt, model=None, **kwargs):
        # Implement your custom query logic
        return f"Custom response to: {prompt}"

    def list_models(self):
        return [
            ModelInfo(
                id="custom-model",
                name="Custom Model",
                provider="custom",
                capabilities=[ModelCapability.TEXT_GENERATION]
            )
        ]

    def check_availability(self):
        # Check if your provider is available
        return True

# Register and use custom provider
registry = ProviderRegistry()
config = ProviderConfig(name="custom")
registry.add_provider(config, CustomProvider)
```

## Model Capabilities

The system supports the following capabilities:

- `TEXT_GENERATION`: General text generation
- `CHAT`: Conversational AI
- `CODE_GENERATION`: Code generation and completion
- `TRANSLATION`: Language translation
- `SUMMARIZATION`: Text summarization
- `EMBEDDING`: Text embeddings for semantic search
- `IMAGE_GENERATION`: Image generation from text
- `AUDIO_GENERATION`: Audio/speech generation
- `VIDEO_GENERATION`: Video generation
- `MODERATION`: Content safety checking

## Error Handling

The system includes comprehensive error handling:

```python
# Automatic fallback on failure
response = manager.query_with_fallback(
    "Your prompt",
    preferred_provider="openrouter"  # Falls back to others if this fails
)

# Check provider availability
provider = registry.get_provider("openai")
if provider and provider.check_availability():
    response = provider.query("Your prompt")
else:
    print("Provider not available")

# Usage statistics for monitoring
stats = manager.get_usage_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Request distribution: {stats['request_counts']}")
```

## Performance Optimization

### Caching
The system respects the global caching settings for repeated queries.

### Connection Pooling
HTTP connections are reused for better performance.

### Timeout Configuration
Configure timeouts per provider:

```python
config = ProviderConfig(
    name="provider",
    timeout=60  # 60 seconds timeout
)
```

## Testing

Run the provider tests:

```bash
# Run all provider tests
pytest tests/unit/providers/

# Run specific test file
pytest tests/unit/providers/test_manager.py

# Run with coverage
pytest tests/unit/providers/ --cov=fazztv.providers
```

## Migration Guide

### From Single Provider to Multi-Provider

Before:
```python
from fazztv.api.openrouter import OpenRouterClient

client = OpenRouterClient()
response = client.query("Your prompt")
```

After:
```python
from fazztv.providers import get_provider_manager

manager = get_provider_manager()
response = manager.query_with_fallback("Your prompt")
```

### Backward Compatibility

The old `OpenRouterClient` in `fazztv.api.openrouter` can be updated to use the new system:

```python
from fazztv.providers import get_provider_manager

class OpenRouterClient:
    def __init__(self, api_key=None):
        self.manager = get_provider_manager()

    def query(self, prompt, **kwargs):
        return self.manager.query_with_fallback(
            prompt,
            preferred_provider="openrouter",
            **kwargs
        )
```

## Best Practices

1. **Always use fallback in production**: Enable fallback to ensure reliability
2. **Monitor usage statistics**: Track provider usage to optimize costs
3. **Set appropriate timeouts**: Adjust timeouts based on your use case
4. **Use capability-based selection**: Let the system choose the best provider
5. **Configure multiple providers**: More providers = better reliability
6. **Keep API keys secure**: Use environment variables, never hardcode keys
7. **Test provider availability**: Check availability before critical operations
8. **Use load balancing for high volume**: Distribute load across providers
9. **Prefer free models for testing**: Use free tier models during development
10. **Implement custom providers carefully**: Follow the BaseProvider interface

## Troubleshooting

### Provider Not Available
- Check API key configuration
- Verify network connectivity
- Check provider service status

### Slow Response Times
- Adjust timeout settings
- Enable load balancing
- Check provider performance metrics

### High Costs
- Use free tier models when possible
- Monitor usage statistics
- Implement caching for repeated queries

### Rate Limiting
- Enable load balancing
- Implement request throttling
- Use multiple API keys

## Future Enhancements

- Support for more providers (Anthropic, Cohere, HuggingFace)
- Advanced routing strategies
- Request caching and deduplication
- Cost tracking and budgeting
- Automatic model selection based on task
- Provider health monitoring
- Request retry with exponential backoff
- Response quality scoring
- Multi-modal support (images, audio, video)