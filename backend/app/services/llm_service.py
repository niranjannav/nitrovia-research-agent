"""LLM service for generating reports and presentations.

This module provides a facade for LLM operations using pydantic-ai with LiteLLM.
Uses pydantic-ai for guaranteed schema compliance across all providers.

The edit_section method is still actively used by the API for editing
individual report sections.
"""

import logging
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel

from app.models.llm_outputs import (
    LLMGeneratedPresentation,
    LLMGeneratedReport,
)
from app.models.schemas import (
    GeneratedPresentation,
    GeneratedReport,
    PresentationSlide,
    ReportSection,
)

logger = logging.getLogger(__name__)

# Prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Type variable for generic structured output
T = TypeVar("T", bound=BaseModel)


def load_prompt(name: str) -> str:
    """
    Load a prompt template from the prompts directory.

    Args:
        name: Prompt file name (without .txt extension)

    Returns:
        Prompt template string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompt_file = PROMPTS_DIR / f"{name}.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_file}")
    logger.info(f"[LLM] Loaded prompt: {name}")
    return prompt_file.read_text(encoding="utf-8")


def get_detail_guidance(detail_level: str) -> str:
    """
    Get the detail guidance for a specific level.

    Args:
        detail_level: "executive", "standard", or "comprehensive"

    Returns:
        Detail guidance text
    """
    try:
        detail_content = load_prompt("detail_levels")
        # Parse the markdown-style sections
        sections = detail_content.split("## ")
        for section in sections:
            if section.startswith(detail_level):
                # Return everything after the first line (the level name)
                lines = section.strip().split("\n", 1)
                if len(lines) > 1:
                    return lines[1].strip()
    except Exception as e:
        logger.warning(f"Failed to load detail guidance: {e}")

    # Fallback guidance
    fallbacks = {
        "executive": "Create a concise executive summary report (1-2 pages equivalent). Focus on key takeaways and actionable recommendations.",
        "standard": "Create a balanced report (3-5 pages equivalent). Include executive summary, analysis, and recommendations.",
        "comprehensive": "Create an in-depth analytical report (5-10 pages equivalent). Provide thorough analysis with detailed findings.",
    }
    return fallbacks.get(detail_level, fallbacks["standard"])


class LLMService:
    """Service for generating reports and presentations.

    Uses pydantic-ai with LiteLLM for guaranteed schema compliance
    across all providers without provider-specific code.
    """

    # Default model for generation
    DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"

    def __init__(self, api_key: str, provider: str = "anthropic"):
        """Initialize LLM service.

        Args:
            api_key: API key for the LLM provider
            provider: Provider name ("anthropic" or "openai")
        """
        import os

        # Set API key in environment for LiteLLM
        if provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
            self.model_string = "anthropic/claude-sonnet-4-20250514"
        elif provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
            self.model_string = "openai/gpt-4o"
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self.model = LiteLLMModel(self.model_string)

    def generate_report(
        self,
        context: str,
        custom_instructions: str | None,
        detail_level: str,
        title_hint: str | None = None,
    ) -> GeneratedReport:
        """
        Generate a structured report from document context.

        Uses pydantic-ai for guaranteed schema compliance.

        Args:
            context: Combined document content
            custom_instructions: User-provided instructions
            detail_level: "executive", "standard", or "comprehensive"
            title_hint: Optional title suggestion

        Returns:
            GeneratedReport with structured content
        """
        # Load prompt template
        try:
            prompt_template = load_prompt("report_generation")
        except FileNotFoundError:
            logger.warning("Report generation prompt not found, using fallback")
            prompt_template = self._get_fallback_report_prompt()

        # Get detail guidance
        detail_guidance = get_detail_guidance(detail_level)

        # Build system prompt
        system_prompt = prompt_template.format(
            detail_level=detail_level.upper(),
            detail_guidance=detail_guidance,
        )

        # Build user content
        user_content = ""
        if custom_instructions:
            user_content += f"USER INSTRUCTIONS:\n{custom_instructions}\n\n"

        if title_hint:
            user_content += f"SUGGESTED TITLE: {title_hint}\n\n"

        user_content += f"SOURCE DOCUMENTS:\n{context}\n\nGenerate the report now."

        try:
            logger.info(f"[LLM] Generating report | detail_level={detail_level}")

            # Create pydantic-ai agent with the output schema
            agent = Agent(
                self.model,
                output_type=LLMGeneratedReport,
                system_prompt=system_prompt,
            )

            # Run synchronously
            result = agent.run_sync(user_content)
            llm_report = result.output

            # Log content stats for debugging
            logger.info(
                f"[LLM] Report generated | title={llm_report.title} | "
                f"sections={len(llm_report.sections)} | "
                f"findings={len(llm_report.key_findings)} | "
                f"recommendations={len(llm_report.recommendations)}"
            )

            # Convert to API schema model for backwards compatibility
            return self._convert_llm_report_to_schema(llm_report)

        except Exception as e:
            logger.error(f"[LLM] Report generation failed: {e}")
            raise

    def _convert_llm_report_to_schema(
        self, llm_report: LLMGeneratedReport
    ) -> GeneratedReport:
        """Convert LLM output model to API schema model."""
        return GeneratedReport(
            title=llm_report.title,
            executive_summary=llm_report.executive_summary,
            sections=[
                ReportSection(
                    title=s.title,
                    content=s.content,
                    subsections=[
                        ReportSection(
                            title=sub.title,
                            content=sub.content,
                            subsections=[],  # Flat structure for LLM outputs
                        )
                        for sub in s.subsections
                    ],
                )
                for s in llm_report.sections
            ],
            key_findings=llm_report.key_findings,
            recommendations=llm_report.recommendations,
            sources=llm_report.sources,
        )

    def generate_presentation(
        self,
        report: GeneratedReport,
        slide_count_min: int,
        slide_count_max: int,
    ) -> GeneratedPresentation:
        """
        Generate a presentation from a report.

        Uses pydantic-ai for guaranteed schema compliance.

        Args:
            report: Generated report to convert
            slide_count_min: Minimum number of slides
            slide_count_max: Maximum number of slides

        Returns:
            GeneratedPresentation with slide structure
        """
        # Load prompt template
        try:
            prompt_template = load_prompt("presentation_generation")
        except FileNotFoundError:
            logger.warning("Presentation prompt not found, using fallback")
            prompt_template = self._get_fallback_presentation_prompt()

        system_prompt = prompt_template.format(
            slide_count_min=slide_count_min,
            slide_count_max=slide_count_max,
        )

        # Format report content for LLM
        sections_text = ""
        for section in report.sections:
            sections_text += f"\n## {section.title}\n{section.content}\n"
            for subsection in section.subsections:
                sections_text += f"\n### {subsection.title}\n{subsection.content}\n"

        user_content = f"""Create a presentation from this report:

TITLE: {report.title}

EXECUTIVE SUMMARY:
{report.executive_summary}

SECTIONS:
{sections_text}

KEY FINDINGS:
{chr(10).join(f'- {f}' for f in report.key_findings)}

RECOMMENDATIONS:
{chr(10).join(f'- {r}' for r in report.recommendations)}

Generate the presentation slides now."""

        try:
            logger.info(
                f"[LLM] Generating presentation | slides={slide_count_min}-{slide_count_max}"
            )

            # Create pydantic-ai agent with the output schema
            agent = Agent(
                self.model,
                output_type=LLMGeneratedPresentation,
                system_prompt=system_prompt,
            )

            # Run synchronously
            result = agent.run_sync(user_content)
            llm_presentation = result.output

            logger.info(
                f"[LLM] Presentation generated | slides={len(llm_presentation.slides)}"
            )

            # Convert to API schema model
            return self._convert_llm_presentation_to_schema(llm_presentation)

        except Exception as e:
            logger.error(f"[LLM] Presentation generation failed: {e}")
            raise

    def _convert_llm_presentation_to_schema(
        self, llm_pres: LLMGeneratedPresentation
    ) -> GeneratedPresentation:
        """Convert LLM output model to API schema model."""
        return GeneratedPresentation(
            title=llm_pres.title,
            slides=[
                PresentationSlide(
                    type=slide.type,
                    title=slide.title,
                    subtitle=slide.subtitle,
                    bullets=slide.bullets,
                    findings=slide.findings,
                    items=slide.items,
                    contact=slide.contact,
                    notes=slide.notes,
                )
                for slide in llm_pres.slides
            ],
        )

    def edit_section(
        self,
        section_title: str,
        section_content: str,
        user_instructions: str,
        report_context: str,
    ) -> str:
        """
        Edit a single section of a report based on user instructions.

        Args:
            section_title: Title of the section being edited
            section_content: Current content of the section
            user_instructions: User's edit request
            report_context: Summary of the full report for context

        Returns:
            Updated section content as plain text
        """
        # Load prompt template
        try:
            prompt_template = load_prompt("section_edit")
        except FileNotFoundError:
            logger.warning("Section edit prompt not found, using fallback")
            prompt_template = self._get_fallback_section_edit_prompt()

        prompt = prompt_template.format(
            section_title=section_title,
            section_content=section_content,
            user_instructions=user_instructions,
            report_context=report_context[:3000],  # Truncate for context window
        )

        try:
            logger.info(f"[LLM] Editing section | title={section_title}")

            # For plain text generation, use a simple agent without output_type
            agent = Agent(
                self.model,
                system_prompt="You are a professional report editor. Return ONLY the updated section content, no additional text or formatting.",
            )

            result = agent.run_sync(prompt)
            new_content = result.output.strip()

            logger.info(f"[LLM] Section edited | chars={len(new_content)}")
            return new_content

        except Exception as e:
            logger.error(f"[LLM] Section edit failed: {e}")
            raise

    def _get_fallback_report_prompt(self) -> str:
        """Fallback prompt if file not found."""
        return """You are an expert research analyst. Create a professional report.

DETAIL LEVEL: {detail_level}
{detail_guidance}

Create a comprehensive report with an executive summary (2-3 paragraphs),
detailed sections with substantive content, at least 2 key findings,
and at least 1 actionable recommendation."""

    def _get_fallback_presentation_prompt(self) -> str:
        """Fallback prompt if file not found."""
        return """Create a presentation with {slide_count_min} to {slide_count_max} slides.

Include a title slide, content slides with bullet points, key findings,
recommendations, and a closing slide."""

    def _get_fallback_section_edit_prompt(self) -> str:
        """Fallback prompt if file not found."""
        return """Edit this section based on user instructions:

Section: {section_title}
Content: {section_content}

User request: {user_instructions}

Context: {report_context}

Return ONLY the updated section content."""
