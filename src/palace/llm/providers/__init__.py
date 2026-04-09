"""
Palace Framework - LLM Providers Module

This module contains implementations of various LLM providers.
Each provider implements the LLMProvider interface, allowing for
easy swapping between different LLM backends.

Available Providers:
    - OllamaProvider: For Ollama Cloud and local Ollama instances
    - OpenAIProvider: For OpenAI API (GPT models) - Future
    - AnthropicProvider: For Anthropic API (Claude models) - Future
    - AzureProvider: For Azure OpenAI Service - Future

The providers module follows the Strategy pattern, allowing the
framework to work with multiple LLM backends through a common interface.

Usage:
    from palace.llm.providers import OllamaProvider, ProviderConfig

    # Create provider
    config = ProviderConfig(
        name="ollama",
        base_url="http://localhost:11434",
        api_key="your-api-key"
    )
    provider = OllamaProvider(config)

    # Invoke model
    response = await provider.invoke(
        prompt="Hello, world!",
        model="qwen3-coder-next"
    )
"""

# Base config (for all providers)
from palace.llm.base import LLMProvider as ProviderInterface
from palace.llm.providers.ollama import (
    OllamaConfig,
    OllamaError,
    OllamaModelInfo,
    OllamaModelStatus,
    OllamaProvider,
)

__all__ = [
    # Ollama
    "OllamaProvider",
    "OllamaConfig",
    "OllamaModelInfo",
    "OllamaModelStatus",
    "OllamaError",
    # Interface
    "ProviderInterface",
]
