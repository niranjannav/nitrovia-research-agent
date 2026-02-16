"""LLM subsystem for unified model access.

This module provides a unified interface for LLM providers with:
- Task-based model routing (different models for different tasks)
- Automatic retry with exponential backoff
- Fallback to alternative providers on failure
- Accurate token counting
- Structured output validation

Example usage:
    from app.llm import ModelGateway, GatewayConfig, TaskType

    config = GatewayConfig(
        anthropic_api_key="...",
        openai_api_key="...",
    )
    gateway = ModelGateway(config)

    # Generate text
    result = await gateway.generate_text(
        task=TaskType.REPORT_GENERATION,
        messages=[{"role": "user", "content": "Generate a report..."}],
    )

    # Generate structured output
    report, usage = await gateway.generate_structured(
        task=TaskType.REPORT_GENERATION,
        output_schema=GeneratedReport,
        messages=[{"role": "user", "content": "..."}],
    )
"""

from .config import (
    DEFAULT_ROUTING_TABLE,
    MODEL_CONFIGS,
    GatewayConfig,
    ModelConfig,
    Provider,
    TaskType,
)
from .gateway import (
    GenerationResult,
    ModelGateway,
    TokenUsage,
    create_gateway_from_settings,
)
from .retry import RetryConfig, RetryStrategy
from .router import ModelRouter
from .token_counter import TokenCounter, get_token_counter

__all__ = [
    # Config
    "GatewayConfig",
    "ModelConfig",
    "Provider",
    "TaskType",
    "MODEL_CONFIGS",
    "DEFAULT_ROUTING_TABLE",
    # Gateway
    "ModelGateway",
    "GenerationResult",
    "TokenUsage",
    "create_gateway_from_settings",
    # Router
    "ModelRouter",
    # Retry
    "RetryConfig",
    "RetryStrategy",
    # Token Counter
    "TokenCounter",
    "get_token_counter",
]
