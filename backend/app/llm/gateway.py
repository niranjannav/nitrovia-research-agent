"""Unified LLM gateway using pydantic-ai with LiteLLM.

Provides a single interface for multiple LLM providers with built-in
retry, timeout, fallback, and structured output support.

Uses pydantic-ai for guaranteed schema compliance across all providers.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

import litellm
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel

from .config import GatewayConfig, ModelConfig, Provider, TaskType
from .retry import (
    RATE_LIMIT_WAIT_SECONDS,
    RetryConfig,
    RetryStrategy,
    is_rate_limit_error,
    is_transient_error,
)
from .router import ModelRouter
from .token_counter import TokenCounter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class TokenUsage:
    """Token usage statistics for a request."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    estimated_cost: float = 0.0


@dataclass
class GenerationResult:
    """Result of an LLM generation request."""

    content: str
    usage: TokenUsage
    model_used: str
    fallback_used: bool = False


class ModelGateway:
    """Unified gateway for LLM providers.

    Provides a single interface for making LLM calls with:
    - Automatic model routing based on task type
    - Retry with exponential backoff
    - Fallback to alternative providers on failure
    - Guaranteed structured output via pydantic-ai
    - Token counting and cost tracking
    """

    def __init__(self, config: GatewayConfig):
        """Initialize the gateway.

        Args:
            config: Gateway configuration
        """
        self.config = config
        self.router = ModelRouter(config)
        self.token_counter = TokenCounter()

        # Configure LiteLLM
        self._configure_litellm()

        # Set up retry strategy
        self.retry_strategy = RetryStrategy(
            RetryConfig(
                max_retries=config.max_retries,
                initial_delay=config.initial_delay,
                max_delay=config.max_delay,
                backoff_factor=config.backoff_factor,
            )
        )

        logger.info(
            f"ModelGateway initialized with providers: "
            f"{[p.value for p in config.get_available_providers()]}"
        )

    def _configure_litellm(self) -> None:
        """Configure LiteLLM with API keys and settings."""
        # Disable LiteLLM's verbose logging
        litellm.set_verbose = False

        # Set API keys as environment-style for LiteLLM
        import os
        if self.config.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.config.anthropic_api_key
        if self.config.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.config.openai_api_key

        # Set timeout
        litellm.request_timeout = self.config.timeout_seconds

    def _get_litellm_model_string(self, model_config: ModelConfig) -> str:
        """Get the LiteLLM model string with provider prefix.

        Args:
            model_config: Model configuration

        Returns:
            LiteLLM-compatible model string (e.g., 'anthropic/claude-sonnet-4-20250514')
        """
        if model_config.provider == Provider.ANTHROPIC:
            return f"anthropic/{model_config.model_id}"
        elif model_config.provider == Provider.OPENAI:
            return f"openai/{model_config.model_id}"
        return model_config.model_id

    async def generate_text(
        self,
        task: TaskType,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate text using the appropriate model for the task.

        Args:
            task: Type of task (determines model selection)
            messages: List of messages [{"role": "user", "content": "..."}]
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens for response (uses model default if not specified)
            temperature: Sampling temperature
            **kwargs: Additional parameters passed to LiteLLM

        Returns:
            GenerationResult with content, usage, and metadata

        Raises:
            Exception: If all models fail
        """
        fallback_chain = self.router.get_fallback_chain(task)

        if not fallback_chain:
            raise ValueError(f"No models available for task: {task.value}")

        last_error: Optional[Exception] = None
        fallback_used = False

        for i, model_config in enumerate(fallback_chain):
            if i > 0:
                fallback_used = True
                logger.info(
                    f"Falling back to {model_config.model_id} "
                    f"(tier {i}) for task {task.value}"
                )

            try:
                result = await self._call_model(
                    model_config=model_config,
                    messages=messages,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens or model_config.max_tokens,
                    temperature=temperature,
                    **kwargs,
                )
                result.fallback_used = fallback_used
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Model {model_config.model_id} failed: {e}"
                )

                # Check if we should try fallback
                if not self.config.enable_fallbacks:
                    raise

                if is_rate_limit_error(e):
                    # Wait before trying next model (they may share org limits)
                    logger.info(
                        f"Rate limit hit on {model_config.model_id}, "
                        f"waiting {RATE_LIMIT_WAIT_SECONDS}s before fallback"
                    )
                    await asyncio.sleep(RATE_LIMIT_WAIT_SECONDS)
                elif not is_transient_error(e):
                    # Non-transient error, might still try fallback
                    if i == len(fallback_chain) - 1:
                        raise

        # All models failed
        if last_error:
            raise last_error
        raise RuntimeError("All models failed with no error captured")

    async def generate_structured(
        self,
        task: TaskType,
        output_schema: type[T],
        messages: list[dict],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> tuple[T, TokenUsage]:
        """Generate structured output matching a Pydantic schema.

        Uses pydantic-ai with LiteLLM for guaranteed schema compliance
        across all providers without provider-specific code.

        Args:
            task: Type of task (determines model selection)
            output_schema: Pydantic model class for the expected output
            messages: List of messages
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens for response
            temperature: Sampling temperature (lower for structured output)
            **kwargs: Additional parameters

        Returns:
            Tuple of (validated Pydantic model, TokenUsage)

        Raises:
            ValidationError: If response doesn't match schema
            Exception: If all models fail
        """
        fallback_chain = self.router.get_fallback_chain(task)

        if not fallback_chain:
            raise ValueError(f"No models available for task: {task.value}")

        last_error: Optional[Exception] = None

        for i, model_config in enumerate(fallback_chain):
            if i > 0:
                logger.info(
                    f"Falling back to {model_config.model_id} "
                    f"for structured output (tier {i})"
                )

            try:
                result = await self._call_model_structured(
                    model_config=model_config,
                    output_schema=output_schema,
                    messages=messages,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens or model_config.max_tokens,
                    temperature=temperature,
                    **kwargs,
                )
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_config.model_id} failed: {e}")
                if not self.config.enable_fallbacks:
                    raise

                if is_rate_limit_error(e):
                    logger.info(
                        f"Rate limit hit on {model_config.model_id}, "
                        f"waiting {RATE_LIMIT_WAIT_SECONDS}s before fallback"
                    )
                    await asyncio.sleep(RATE_LIMIT_WAIT_SECONDS)
                elif i == len(fallback_chain) - 1:
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("All models failed")

    async def _call_model(
        self,
        model_config: ModelConfig,
        messages: list[dict],
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        **kwargs: Any,
    ) -> GenerationResult:
        """Make an LLM call with retry logic.

        Args:
            model_config: Model configuration
            messages: Messages to send
            system_prompt: System prompt
            max_tokens: Max tokens
            temperature: Temperature
            **kwargs: Additional params

        Returns:
            GenerationResult
        """
        # Build request
        request_messages = list(messages)
        if system_prompt:
            # Insert system message at the beginning
            request_messages.insert(0, {"role": "system", "content": system_prompt})

        async def make_request() -> GenerationResult:
            response = await litellm.acompletion(
                model=self._get_litellm_model_string(model_config),
                messages=request_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.config.timeout_seconds,
                **kwargs,
            )

            content = response.choices[0].message.content or ""
            usage = response.usage

            token_usage = TokenUsage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                model=model_config.model_id,
                estimated_cost=self.token_counter.estimate_cost(
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                    model_config.model_id,
                ),
            )

            logger.info(
                f"[LLM] Generated text | model={model_config.model_id} | "
                f"input_tokens={token_usage.input_tokens} | "
                f"output_tokens={token_usage.output_tokens} | "
                f"cost=${token_usage.estimated_cost:.4f}"
            )

            return GenerationResult(
                content=content,
                usage=token_usage,
                model_used=model_config.model_id,
            )

        # Execute with retry
        return await self.retry_strategy.execute_with_retry(make_request)

    async def _call_model_structured(
        self,
        model_config: ModelConfig,
        output_schema: type[T],
        messages: list[dict],
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        **kwargs: Any,
    ) -> tuple[T, TokenUsage]:
        """Make an LLM call for structured output using pydantic-ai.

        Uses pydantic-ai Agent with LiteLLMModel for guaranteed schema
        compliance. No provider-specific code needed.

        Args:
            model_config: Model configuration
            output_schema: Pydantic schema class
            messages: Messages to send
            system_prompt: System prompt
            max_tokens: Max tokens
            temperature: Temperature
            **kwargs: Additional params

        Returns:
            Tuple of (validated Pydantic model, TokenUsage)
        """
        # Create LiteLLM model for pydantic-ai
        litellm_model_string = self._get_litellm_model_string(model_config)
        model = LiteLLMModel(litellm_model_string)

        # Create pydantic-ai agent with the output schema
        agent = Agent(
            model,
            output_type=output_schema,
            system_prompt=system_prompt or "",
        )

        # Extract user message from messages list
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        async def make_request() -> tuple[T, TokenUsage]:
            # Run the agent - pydantic-ai handles structured output enforcement
            result = await agent.run(user_message)

            # Extract usage from result
            usage = result.usage()

            token_usage = TokenUsage(
                input_tokens=usage.request_tokens or 0,
                output_tokens=usage.response_tokens or 0,
                total_tokens=(usage.request_tokens or 0) + (usage.response_tokens or 0),
                model=model_config.model_id,
                estimated_cost=self.token_counter.estimate_cost(
                    usage.request_tokens or 0,
                    usage.response_tokens or 0,
                    model_config.model_id,
                ),
            )

            logger.info(
                f"[LLM] Generated structured output | model={model_config.model_id} | "
                f"schema={output_schema.__name__} | "
                f"input_tokens={token_usage.input_tokens} | "
                f"output_tokens={token_usage.output_tokens}"
            )

            # result.output is the validated Pydantic model
            return result.output, token_usage

        return await self.retry_strategy.execute_with_retry(make_request)

    def count_tokens(self, text: str, task: TaskType) -> int:
        """Count tokens for text using the primary model for a task.

        Args:
            text: Text to count tokens for
            task: Task type (determines which model's tokenizer to use)

        Returns:
            Token count
        """
        model = self.router.get_primary_model(task)
        if model:
            return self.token_counter.count_tokens(text, model.model_id)
        return self.token_counter.count_tokens(text, "claude-sonnet-4")

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        task: TaskType,
    ) -> float:
        """Estimate cost for a request.

        Args:
            input_tokens: Input token count
            output_tokens: Output token count
            task: Task type

        Returns:
            Estimated cost in USD
        """
        model = self.router.get_primary_model(task)
        if model:
            return self.token_counter.estimate_cost(
                input_tokens, output_tokens, model.model_id
            )
        return 0.0


# Convenience function for creating a gateway from settings
def create_gateway_from_settings() -> ModelGateway:
    """Create a ModelGateway from application settings.

    Returns:
        Configured ModelGateway instance
    """
    # Import here to avoid circular imports
    from app.config import settings

    config = GatewayConfig(
        anthropic_api_key=settings.anthropic_api_key,
        openai_api_key=getattr(settings, "openai_api_key", None),
        max_retries=getattr(settings, "llm_max_retries", 3),
        timeout_seconds=getattr(settings, "llm_timeout_seconds", 120),
        enable_fallbacks=getattr(settings, "llm_enable_fallbacks", True),
    )

    return ModelGateway(config)
