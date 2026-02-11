"""Model routing logic for task-based model selection.

Routes LLM tasks to appropriate models based on task type,
with support for fallback chains when providers fail.
"""

import logging
from typing import Optional

from .config import (
    DEFAULT_ROUTING_TABLE,
    MODEL_CONFIGS,
    GatewayConfig,
    ModelConfig,
    Provider,
    TaskType,
)

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes tasks to appropriate models with fallback support."""

    def __init__(self, config: GatewayConfig):
        """Initialize router with gateway configuration.

        Args:
            config: Gateway configuration with API keys and routing table
        """
        self.config = config
        self.routing_table = config.get_routing_table()
        self.available_providers = config.get_available_providers()

    def get_model(
        self, task: TaskType, fallback_tier: int = 0
    ) -> Optional[ModelConfig]:
        """Get the appropriate model for a task.

        Args:
            task: Type of task to route
            fallback_tier: Which fallback to use (0 = primary, 1 = first fallback, etc.)

        Returns:
            ModelConfig for the selected model, or None if no model available
        """
        model_chain = self._get_available_chain(task)

        if fallback_tier >= len(model_chain):
            logger.warning(
                f"No model available for task={task.value} at tier={fallback_tier}"
            )
            return None

        model_key = model_chain[fallback_tier]
        model_config = MODEL_CONFIGS.get(model_key)

        if model_config:
            logger.debug(
                f"Routed task={task.value} to model={model_key} (tier={fallback_tier})"
            )

        return model_config

    def get_fallback_chain(self, task: TaskType) -> list[ModelConfig]:
        """Get ordered list of available models for a task.

        Args:
            task: Type of task to route

        Returns:
            List of ModelConfig objects in priority order
        """
        model_chain = self._get_available_chain(task)
        return [MODEL_CONFIGS[key] for key in model_chain if key in MODEL_CONFIGS]

    def _get_available_chain(self, task: TaskType) -> list[str]:
        """Get list of model keys available for a task (filtered by provider availability).

        Args:
            task: Type of task to route

        Returns:
            List of model keys that are available
        """
        all_models = self.routing_table.get(task, DEFAULT_ROUTING_TABLE.get(task, []))

        # Filter to only models whose providers are available
        available = []
        for model_key in all_models:
            model_config = MODEL_CONFIGS.get(model_key)
            if model_config and model_config.provider in self.available_providers:
                available.append(model_key)

        return available

    def get_primary_model(self, task: TaskType) -> Optional[ModelConfig]:
        """Get the primary (first choice) model for a task.

        Args:
            task: Type of task to route

        Returns:
            ModelConfig for the primary model
        """
        return self.get_model(task, fallback_tier=0)

    def has_fallback(self, task: TaskType) -> bool:
        """Check if a task has fallback models available.

        Args:
            task: Type of task to check

        Returns:
            True if at least one fallback model is available
        """
        chain = self._get_available_chain(task)
        return len(chain) > 1

    def get_next_fallback(
        self, task: TaskType, current_model: ModelConfig
    ) -> Optional[ModelConfig]:
        """Get the next fallback model after the current one.

        Args:
            task: Type of task
            current_model: The model that failed

        Returns:
            Next ModelConfig in the chain, or None if no more fallbacks
        """
        chain = self._get_available_chain(task)

        # Find current model in chain
        current_key = None
        for key, config in MODEL_CONFIGS.items():
            if config.model_id == current_model.model_id:
                current_key = key
                break

        if current_key is None or current_key not in chain:
            return None

        current_index = chain.index(current_key)
        next_index = current_index + 1

        if next_index >= len(chain):
            return None

        return MODEL_CONFIGS.get(chain[next_index])
