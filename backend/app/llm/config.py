"""LLM configuration and model definitions.

This module defines task types, model configurations, and routing tables
for the unified LLM gateway.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskType(Enum):
    """Types of LLM tasks with different model requirements."""

    SUMMARIZATION = "summarization"  # Document summarization (cheap, fast)
    REPORT_GENERATION = "report_generation"  # Main report generation (high quality)
    PRESENTATION_GEN = "presentation_generation"  # Slide generation (high quality)
    SECTION_EDIT = "section_edit"  # Editing individual sections (medium)
    CLASSIFICATION = "classification"  # Content classification (fast)
    SKILL_PLANNING = "skill_planning"  # Skill selection agent (fast)
    RESEARCH = "research"  # Research agent with tools (high quality)


class Provider(Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    provider: Provider
    model_id: str
    max_tokens: int
    supports_structured_output: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    context_window: int = 128000

    @property
    def litellm_model(self) -> str:
        """Get the LiteLLM-compatible model identifier."""
        if self.provider == Provider.ANTHROPIC:
            return self.model_id  # LiteLLM uses anthropic model IDs directly
        elif self.provider == Provider.OPENAI:
            return self.model_id
        return self.model_id


# Available model configurations
MODEL_CONFIGS: dict[str, ModelConfig] = {
    # Anthropic models
    "claude-sonnet-4": ModelConfig(
        provider=Provider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
        max_tokens=8192,
        supports_structured_output=True,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200000,
    ),
    "claude-3-5-haiku": ModelConfig(
        provider=Provider.ANTHROPIC,
        model_id="claude-3-5-haiku-20241022",
        max_tokens=8192,
        supports_structured_output=True,
        cost_per_1k_input=0.0008,
        cost_per_1k_output=0.004,
        context_window=200000,
    ),
    # OpenAI models
    "gpt-4o": ModelConfig(
        provider=Provider.OPENAI,
        model_id="gpt-4o",
        max_tokens=16384,
        supports_structured_output=True,
        cost_per_1k_input=0.0025,
        cost_per_1k_output=0.01,
        context_window=128000,
    ),
    "gpt-4o-mini": ModelConfig(
        provider=Provider.OPENAI,
        model_id="gpt-4o-mini",
        max_tokens=16384,
        supports_structured_output=True,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        context_window=128000,
    ),
}

# Default routing table: task -> ordered list of model keys (primary, fallbacks)
DEFAULT_ROUTING_TABLE: dict[TaskType, list[str]] = {
    TaskType.SUMMARIZATION: ["claude-3-5-haiku", "gpt-4o-mini"],
    TaskType.REPORT_GENERATION: ["claude-sonnet-4", "gpt-4o"],
    TaskType.PRESENTATION_GEN: ["claude-sonnet-4", "gpt-4o"],
    TaskType.SECTION_EDIT: ["claude-sonnet-4", "gpt-4o-mini"],
    TaskType.CLASSIFICATION: ["claude-3-5-haiku", "gpt-4o-mini"],
    TaskType.SKILL_PLANNING: ["claude-3-5-haiku", "gpt-4o-mini"],
    TaskType.RESEARCH: ["claude-sonnet-4", "gpt-4o"],
}


@dataclass
class GatewayConfig:
    """Configuration for the LLM gateway."""

    # API keys
    anthropic_api_key: str
    openai_api_key: Optional[str] = None

    # Retry configuration
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0

    # Timeout configuration
    timeout_seconds: int = 120

    # Fallback behavior
    enable_fallbacks: bool = True

    # Rate limiting (requests per minute)
    rate_limit_rpm: Optional[int] = None

    # Custom routing table (overrides defaults)
    routing_table: Optional[dict[TaskType, list[str]]] = None

    def get_routing_table(self) -> dict[TaskType, list[str]]:
        """Get the effective routing table."""
        if self.routing_table:
            return self.routing_table
        return DEFAULT_ROUTING_TABLE

    def get_available_providers(self) -> set[Provider]:
        """Get set of providers with configured API keys."""
        providers = {Provider.ANTHROPIC}  # Always have Anthropic
        if self.openai_api_key:
            providers.add(Provider.OPENAI)
        return providers
