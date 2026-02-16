"""Accurate token counting for LLM requests.

Uses tiktoken for OpenAI models and estimation for Anthropic models
(since Anthropic doesn't provide a public tokenizer).
"""

import logging
from functools import lru_cache
from typing import Optional

import tiktoken

from .config import MODEL_CONFIGS, ModelConfig, Provider

logger = logging.getLogger(__name__)


class TokenCounter:
    """Counts tokens for different LLM providers."""

    # Anthropic uses roughly 3.5-4 characters per token on average
    ANTHROPIC_CHARS_PER_TOKEN = 3.8

    def __init__(self):
        """Initialize token counter."""
        self._openai_encoders: dict[str, tiktoken.Encoding] = {}

    @lru_cache(maxsize=10)
    def _get_openai_encoder(self, model: str) -> tiktoken.Encoding:
        """Get tiktoken encoder for an OpenAI model.

        Args:
            model: OpenAI model ID

        Returns:
            tiktoken Encoding instance
        """
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base for unknown models
            logger.debug(f"Unknown model {model}, using cl100k_base encoding")
            return tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text for a specific model.

        Args:
            text: Text to count tokens for
            model: Model ID or model key

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Get model config
        model_config = self._get_model_config(model)

        if model_config is None:
            # Unknown model, use rough estimation
            return self._estimate_tokens(text)

        if model_config.provider == Provider.OPENAI:
            return self._count_openai_tokens(text, model_config.model_id)
        elif model_config.provider == Provider.ANTHROPIC:
            return self._count_anthropic_tokens(text)
        else:
            return self._estimate_tokens(text)

    def _count_openai_tokens(self, text: str, model_id: str) -> int:
        """Count tokens using tiktoken for OpenAI models.

        Args:
            text: Text to count
            model_id: OpenAI model ID

        Returns:
            Exact token count
        """
        try:
            encoder = self._get_openai_encoder(model_id)
            return len(encoder.encode(text))
        except Exception as e:
            logger.warning(f"tiktoken encoding failed: {e}, using estimation")
            return self._estimate_tokens(text)

    def _count_anthropic_tokens(self, text: str) -> int:
        """Estimate tokens for Anthropic models.

        Anthropic doesn't provide a public tokenizer, so we estimate based on
        character count. Claude models use roughly 3.5-4 characters per token.

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        return int(len(text) / self.ANTHROPIC_CHARS_PER_TOKEN)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation when model is unknown.

        Args:
            text: Text to count

        Returns:
            Rough token estimate
        """
        # Use 4 characters per token as a conservative estimate
        return len(text) // 4

    def _get_model_config(self, model: str) -> Optional[ModelConfig]:
        """Get ModelConfig for a model ID or key.

        Args:
            model: Model key or model ID

        Returns:
            ModelConfig if found
        """
        # Check if it's a model key
        if model in MODEL_CONFIGS:
            return MODEL_CONFIGS[model]

        # Check if it matches a model_id
        for config in MODEL_CONFIGS.values():
            if config.model_id == model:
                return config

        return None

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> float:
        """Estimate cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model key or model ID

        Returns:
            Estimated cost in USD
        """
        model_config = self._get_model_config(model)

        if model_config is None:
            logger.warning(f"Unknown model {model}, cannot estimate cost")
            return 0.0

        input_cost = (input_tokens / 1000) * model_config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model_config.cost_per_1k_output

        return input_cost + output_cost

    def count_messages_tokens(
        self,
        messages: list[dict],
        model: str,
    ) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model ID or key

        Returns:
            Total token count including message overhead
        """
        total = 0

        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                total += self.count_tokens(content, model)
            elif isinstance(content, list):
                # Handle multi-part content (e.g., with images)
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += self.count_tokens(part.get("text", ""), model)

            # Add overhead for message structure (role, etc.)
            # OpenAI adds ~4 tokens per message, Anthropic similar
            total += 4

        # Add overhead for the overall message structure
        total += 3

        return total

    def fits_in_context(
        self,
        text: str,
        model: str,
        reserved_output_tokens: int = 0,
    ) -> bool:
        """Check if text fits within the model's context window.

        Args:
            text: Text to check
            model: Model key or model ID
            reserved_output_tokens: Tokens to reserve for output

        Returns:
            True if text fits
        """
        model_config = self._get_model_config(model)

        if model_config is None:
            # Unknown model, assume 100k context as default
            context_window = 100000
        else:
            context_window = model_config.context_window

        token_count = self.count_tokens(text, model)
        available = context_window - reserved_output_tokens

        return token_count <= available

    def get_available_output_tokens(
        self,
        input_tokens: int,
        model: str,
    ) -> int:
        """Calculate available tokens for output given input size.

        Args:
            input_tokens: Number of input tokens
            model: Model key or model ID

        Returns:
            Available tokens for output
        """
        model_config = self._get_model_config(model)

        if model_config is None:
            # Unknown model, assume 100k context
            context_window = 100000
            max_output = 8192
        else:
            context_window = model_config.context_window
            max_output = model_config.max_tokens

        available = context_window - input_tokens

        # Cap at model's max output tokens
        return min(available, max_output)


# Singleton instance for convenience
_token_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get the singleton TokenCounter instance."""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter
