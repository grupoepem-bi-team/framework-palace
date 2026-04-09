"""
Palace Framework - LLM Module

This module provides a unified interface for interacting with multiple LLM providers,
with support for model routing based on agent roles, cost tracking, and extensibility.

Key Components:
    - LLMClient: Main client for invoking LLM models
    - LLMRouter: Routes requests to appropriate models based on roles
    - LLMProvider: Abstract base for LLM providers (Ollama, OpenAI, etc.)
    - CostTracker: Tracks token usage and costs

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                         LLMClient                               │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │                        LLMRouter                         │   │
    │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
    │  │  │   Coder     │  │    DBA      │  │  Reviewer   │      │   │
    │  │  │   Model     │  │   Model     │  │   Model     │      │   │
    │  │  └─────────────┘  └─────────────┘  └─────────────┘      │   │
    │  └─────────────────────────────────────────────────────────┘   │
    │                              │                                  │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │                    Provider Layer                        │   │
    │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
    │  │  │   Ollama    │  │   OpenAI    │  │   Anthropic │      │   │
    │  │  │   Provider  │  │   Provider  │  │   Provider  │      │   │
    │  │  └─────────────┘  └─────────────┘  └─────────────┘      │   │
    │  └─────────────────────────────────────────────────────────┘   │
    │                              │                                  │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │                    Cost Tracker                          │   │
    │  │  • Token counting    • Cost estimation    • Usage stats │   │
    │  └─────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    from palace.llm import LLMClient, LLMRouter

    # Create client with configuration
    client = LLMClient(config)

    # Invoke with automatic model routing
    response = await client.invoke(
        prompt="Write a REST endpoint",
        role="backend"
    )

    # Invoke with specific model
    response = await client.invoke(
        prompt="Explain this code",
        model="qwen3-coder-next"
    )

    # Get usage statistics
    stats = client.get_usage_stats()
"""

# Base classes and types
from palace.llm.base import (
    LLMError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMProvider,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMRole,
    LLMTimeoutError,
)

# Client and router
from palace.llm.client import LLMClient, get_llm_client

# Cost tracking
from palace.llm.costs import CostEstimate, CostTracker, PricingTier, UsageStats

# Exceptions
from palace.llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContentFilterError,
    LLMContextLengthExceededError,
    LLMProviderError,
    LLMResponseParseError,
    LLMValidationError,
)

# Model definitions
from palace.llm.models import (
    LLMModel,
    LLMModelConfig,
    ModelCapability,
    ModelProvider,
    ModelRegistry,
)
from palace.llm.providers.base import ProviderConfig

# Providers
from palace.llm.providers.ollama import OllamaProvider
from palace.llm.router import LLMRouter, RoleModelMapping, RoutingStrategy

# Version
__version__ = "0.1.0"

__all__ = [
    # Base classes
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "LLMMessage",
    "LLMRole",
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMModelNotFoundError",
    # Client and router
    "LLMClient",
    "LLMRouter",
    "RoleModelMapping",
    "RoutingStrategy",
    "get_llm_client",
    # Cost tracking
    "CostTracker",
    "CostEstimate",
    "UsageStats",
    "PricingTier",
    # Models
    "LLMModel",
    "LLMModelConfig",
    "ModelRegistry",
    "ModelCapability",
    "ModelProvider",
    # Providers
    "OllamaProvider",
    "ProviderConfig",
    # Exceptions
    "LLMAuthenticationError",
    "LLMConnectionError",
    "LLMContentFilterError",
    "LLMContextLengthExceededError",
    "LLMProviderError",
    "LLMResponseParseError",
    "LLMValidationError",
]
