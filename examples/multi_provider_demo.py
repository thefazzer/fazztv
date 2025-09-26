#!/usr/bin/env python3
"""
Multi-Provider System Demo

This script demonstrates the multi-provider system capabilities including:
- Automatic fallback
- Load balancing
- Capability-based selection
- Cost optimization
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fazztv.providers import (
    get_provider_manager,
    ProviderConfigLoader,
    ModelCapability
)


def demo_basic_usage():
    """Demonstrate basic provider usage."""
    print("\n=== Basic Usage Demo ===")

    # Get provider manager with default configuration
    manager = get_provider_manager()

    # Simple query with automatic provider selection
    response = manager.query_with_fallback(
        "What are the three laws of robotics?"
    )

    if response:
        print(f"Response: {response[:200]}...")
    else:
        print("No response received")


def demo_fallback():
    """Demonstrate automatic fallback."""
    print("\n=== Fallback Demo ===")

    manager = get_provider_manager()

    # Query with preferred provider that might fail
    response = manager.query_with_fallback(
        "Explain quantum entanglement",
        preferred_provider="openrouter"  # Will fallback if this fails
    )

    if response:
        print(f"Response received (with fallback if needed): {response[:200]}...")
    else:
        print("All providers failed")


def demo_capability_selection():
    """Demonstrate capability-based provider selection."""
    print("\n=== Capability Selection Demo ===")

    manager = get_provider_manager()

    # Find provider for code generation
    provider = manager.find_best_provider(ModelCapability.CODE_GENERATION)
    if provider:
        print(f"Best provider for code generation: {provider.get_name()}")

    # Find provider for translation
    provider = manager.find_best_provider(ModelCapability.TRANSLATION)
    if provider:
        print(f"Best provider for translation: {provider.get_name()}")


def demo_cost_optimization():
    """Demonstrate cost optimization."""
    print("\n=== Cost Optimization Demo ===")

    manager = get_provider_manager()

    # Get cheapest model for text generation
    cheapest = manager.registry.get_cheapest_model(
        capability=ModelCapability.TEXT_GENERATION
    )

    if cheapest:
        print(f"Cheapest model: {cheapest.name}")
        print(f"Provider: {cheapest.provider}")
        print(f"Free tier: {cheapest.free_tier}")
        print(f"Cost per token: {cheapest.cost_per_token}")


def demo_compare_providers():
    """Demonstrate comparing responses from multiple providers."""
    print("\n=== Provider Comparison Demo ===")

    manager = get_provider_manager()

    prompt = "Write a haiku about programming"

    # Get available providers
    available = manager.registry.list_providers()
    print(f"Available providers: {available}")

    if len(available) > 1:
        # Compare responses from multiple providers
        responses = manager.compare_responses(prompt)

        for provider, response in responses.items():
            print(f"\n{provider}:")
            print(f"  {response}")


def demo_batch_processing():
    """Demonstrate batch processing."""
    print("\n=== Batch Processing Demo ===")

    manager = get_provider_manager()

    prompts = [
        "Translate 'Hello world' to Spanish",
        "Translate 'Hello world' to French",
        "Translate 'Hello world' to German"
    ]

    responses = manager.batch_query(prompts)

    for prompt, response in zip(prompts, responses):
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response}")


def demo_usage_tracking():
    """Demonstrate usage tracking."""
    print("\n=== Usage Tracking Demo ===")

    manager = get_provider_manager()

    # Make some queries
    for i in range(3):
        manager.query_with_fallback(f"Test query {i}")

    # Get usage statistics
    stats = manager.get_usage_stats()

    print(f"Total requests: {stats['total_requests']}")
    print(f"Request distribution: {stats['request_counts']}")
    print(f"Fallback enabled: {stats['fallback_enabled']}")
    print(f"Load balancing: {stats['load_balancing']}")


def demo_provider_info():
    """Display information about available providers."""
    print("\n=== Provider Information ===")

    manager = get_provider_manager()

    # Get registry summary
    summary = manager.registry.get_summary()

    print(f"Total providers: {summary['total_providers']}")
    print(f"Available providers: {summary['available_providers']}")

    for name, info in summary['providers'].items():
        print(f"\n{name}:")
        print(f"  Available: {info['available']}")
        print(f"  Default model: {info['default_model']}")
        print(f"  Capabilities: {', '.join(info['capabilities'])}")


def demo_list_models():
    """List all available models."""
    print("\n=== Available Models ===")

    manager = get_provider_manager()

    # Get all models
    models = manager.registry.get_all_models()

    print(f"Total models available: {len(models)}")

    # Group by provider
    by_provider = {}
    for model in models:
        if model.provider not in by_provider:
            by_provider[model.provider] = []
        by_provider[model.provider].append(model)

    for provider, provider_models in by_provider.items():
        print(f"\n{provider} ({len(provider_models)} models):")
        for model in provider_models[:3]:  # Show first 3 models
            print(f"  - {model.name}")
            if model.free_tier:
                print(f"    (FREE)")


def main():
    """Run all demos."""
    print("=" * 60)
    print("Multi-Provider System Demo")
    print("=" * 60)

    # Check if any API keys are configured
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))

    if not has_openrouter and not has_openai:
        print("\n⚠️  WARNING: No API keys configured!")
        print("Set OPENROUTER_API_KEY or OPENAI_API_KEY environment variables")
        print("The demo will still run but may have limited functionality.\n")

    # Run demos
    try:
        demo_provider_info()
        demo_list_models()
        demo_capability_selection()
        demo_cost_optimization()

        # These demos require actual API calls
        if has_openrouter or has_openai:
            demo_basic_usage()
            demo_fallback()
            demo_compare_providers()
            demo_batch_processing()
            demo_usage_tracking()
        else:
            print("\n⚠️  Skipping demos that require API calls")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()