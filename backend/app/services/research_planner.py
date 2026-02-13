"""Research planner service for generating expanded research questions.

Takes a user's title and prompt, then generates a set of targeted
research questions that will be used for similarity search against
the indexed document chunks.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm import GatewayConfig, ModelGateway, TaskType

logger = logging.getLogger(__name__)


class ResearchPlan(BaseModel):
    """Structured research plan with expanded questions."""

    title: str = Field(..., description="Research title")
    summary: str = Field(
        ..., description="Brief summary of the research approach"
    )
    questions: list[str] = Field(
        ...,
        description="Expanded research questions for similarity search",
        min_length=3,
        max_length=10,
    )


RESEARCH_PLANNING_PROMPT = """You are a research planning assistant. Given a report title and user instructions, generate a focused set of research questions that will be used to search through document collections.

Your task:
1. Understand the user's research intent from the title and instructions
2. Generate 5-8 specific, targeted research questions that:
   - Cover different aspects of the topic
   - Are specific enough for effective similarity search
   - Range from broad overview questions to specific detail questions
   - Would retrieve relevant information from source documents

Keep questions concise and search-friendly. Each question should target a different dimension of the topic.

{file_descriptions}"""


class ResearchPlanner:
    """Plans research by generating targeted questions from title + prompt.

    These questions serve as the basis for similarity search against
    indexed document chunks in pgvector.
    """

    def __init__(self):
        """Initialize with LLM gateway."""
        settings = get_settings()
        gateway_config = GatewayConfig(
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=getattr(settings, "openai_api_key", None),
        )
        self.gateway = ModelGateway(gateway_config)

    async def generate_research_plan(
        self,
        title: str,
        custom_instructions: str | None = None,
        file_descriptions: list[str] | None = None,
    ) -> ResearchPlan:
        """Generate a research plan with expanded questions.

        Uses a low-cost model (Haiku/GPT-4o-mini) to generate questions
        that will drive the similarity search.

        Args:
            title: Report title indicating the research topic
            custom_instructions: Optional user-provided instructions/prompt
            file_descriptions: Optional list of source file descriptions for context

        Returns:
            ResearchPlan with title and expanded questions
        """
        # Build file context if descriptions are available
        file_context = ""
        if file_descriptions:
            file_context = "Available source documents:\n" + "\n".join(
                f"- {desc}" for desc in file_descriptions
            )

        system_prompt = RESEARCH_PLANNING_PROMPT.format(
            file_descriptions=file_context
        )

        user_message = f"Title: {title}\n"
        if custom_instructions:
            user_message += f"\nUser instructions: {custom_instructions}\n"
        user_message += "\nGenerate the research plan with targeted questions."

        try:
            # Use SUMMARIZATION task type to route to a low-cost model (Haiku)
            plan, usage = await self.gateway.generate_structured(
                task=TaskType.SUMMARIZATION,
                output_schema=ResearchPlan,
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
                max_tokens=2000,
            )

            logger.info(
                f"Research plan generated: {len(plan.questions)} questions, "
                f"input_tokens={usage.input_tokens}, output_tokens={usage.output_tokens}"
            )

            return plan

        except Exception as e:
            logger.error(f"Research plan generation failed: {e}")
            # Fallback: generate basic questions from the title
            return self._fallback_plan(title, custom_instructions)

    def _fallback_plan(
        self,
        title: str,
        custom_instructions: str | None = None,
    ) -> ResearchPlan:
        """Generate a basic research plan without LLM.

        Used as a fallback when the LLM call fails.

        Args:
            title: Report title
            custom_instructions: Optional user instructions

        Returns:
            Basic ResearchPlan
        """
        questions = [
            f"What are the main findings related to {title}?",
            f"What data and evidence support the conclusions about {title}?",
            f"What are the key trends and patterns in {title}?",
            f"What recommendations can be made based on {title}?",
            f"What are the challenges and limitations related to {title}?",
        ]

        if custom_instructions:
            questions.append(custom_instructions)

        return ResearchPlan(
            title=title,
            summary=f"Research plan for: {title}",
            questions=questions,
        )
