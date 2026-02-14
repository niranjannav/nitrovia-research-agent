"""Generate presentation node for the report workflow.

Generates presentation slides from the report content.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.llm import GatewayConfig, ModelGateway, TaskType
from app.models.llm_outputs import LLMGeneratedPresentation
from app.models.schemas import GeneratedPresentation, PresentationSlide
from app.workflows.state import (
    ReportWorkflowState,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
    update_token_metrics,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_file = PROMPTS_DIR / f"{name}.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt not found: {prompt_file}")


def _get_fallback_presentation_prompt() -> str:
    """Fallback prompt if file not found."""
    return """Create a presentation with {slide_count_min} to {slide_count_max} slides.

Include a title slide, content slides with bullet points, key findings,
recommendations, and a closing slide. Use stat_callout, comparison,
timeline, and chart slides when data warrants it."""


def _convert_llm_presentation_to_schema(
    llm_pres: LLMGeneratedPresentation,
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
                stat_value=slide.stat_value,
                stat_context=slide.stat_context,
                left_items=slide.left_items,
                right_items=slide.right_items,
                left_label=slide.left_label,
                right_label=slide.right_label,
                events=slide.events,
                chart_type=slide.chart_type,
                chart_title=slide.chart_title,
                data_labels=slide.data_labels,
                data_values=slide.data_values,
                contact=slide.contact,
                notes=slide.notes,
            )
            for slide in llm_pres.slides
        ],
    )


def should_generate_presentation(state: ReportWorkflowState) -> bool:
    """Check if presentation should be generated.

    Args:
        state: Current workflow state

    Returns:
        True if PPTX is in output formats
    """
    config = state.get("config", {})
    output_formats = config.get("output_formats", ["pdf"])
    return "pptx" in output_formats


async def generate_presentation_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Generate presentation slides from the report.

    Only runs if PPTX is in the requested output formats.

    Args:
        state: Current workflow state with generated report

    Returns:
        Updated state with generated presentation
    """
    report_id = state["report_id"]
    config = state.get("config", {})
    generated_report = state.get("generated_report")
    started_at = datetime.utcnow()

    # Check if we should generate presentation
    if not should_generate_presentation(state):
        logger.info(f"[WORKFLOW] Report {report_id} | PRESENTATION | SKIPPED | No PPTX requested")
        state = update_progress(state, WorkflowStep.GENERATING_PRESENTATION, 80, "Skipping presentation")
        return state

    logger.info(f"[WORKFLOW] Report {report_id} | PRESENTATION | Generating slides...")

    state = update_progress(
        state,
        WorkflowStep.GENERATING_PRESENTATION,
        65,
        "Creating presentation slides...",
    )

    if not generated_report:
        return mark_failed(state, "No report available for presentation generation")

    try:
        # Create gateway
        gateway_config = GatewayConfig(
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=getattr(settings, "openai_api_key", None),
        )
        gateway = ModelGateway(gateway_config)

        # Load prompt template
        try:
            prompt_template = _load_prompt("presentation_generation")
        except FileNotFoundError:
            logger.warning("Presentation prompt not found, using fallback")
            prompt_template = _get_fallback_presentation_prompt()

        # Get slide count configuration
        slide_count_min = config.get("slide_count_min", 10)
        slide_count_max = config.get("slide_count_max", 15)

        system_prompt = prompt_template.format(
            slide_count_min=slide_count_min,
            slide_count_max=slide_count_max,
            skill_context="",
        )

        # Format report content for LLM
        sections_text = ""
        for section in generated_report.sections:
            sections_text += f"\n## {section.title}\n{section.content}\n"
            for subsection in section.subsections:
                sections_text += f"\n### {subsection.title}\n{subsection.content}\n"

        user_content = f"""Create a presentation from this report:

TITLE: {generated_report.title}

EXECUTIVE SUMMARY:
{generated_report.executive_summary}

SECTIONS:
{sections_text}

KEY FINDINGS:
{chr(10).join(f'- {f}' for f in generated_report.key_findings)}

RECOMMENDATIONS:
{chr(10).join(f'- {r}' for r in generated_report.recommendations)}

Generate the presentation slides now."""

        logger.info(
            f"[WORKFLOW] Report {report_id} | PRESENTATION | "
            f"Calling LLM for {slide_count_min}-{slide_count_max} slides"
        )

        # Generate structured output
        llm_presentation, usage = await gateway.generate_structured(
            task=TaskType.PRESENTATION_GEN,
            output_schema=LLMGeneratedPresentation,
            messages=[{"role": "user", "content": user_content}],
            system_prompt=system_prompt,
            max_tokens=4000,
        )

        # Convert to API schema
        generated_presentation = _convert_llm_presentation_to_schema(llm_presentation)

        logger.info(
            f"[WORKFLOW] Report {report_id} | PRESENTATION | COMPLETED | "
            f"{len(generated_presentation.slides)} slides"
        )

        # Update state
        state = {
            **state,
            "generated_presentation": generated_presentation,
        }

        state = update_token_metrics(
            state,
            usage.input_tokens,
            usage.output_tokens,
            usage.estimated_cost,
        )
        state = update_progress(state, WorkflowStep.GENERATING_PRESENTATION, 80, "Presentation created")
        state = mark_step_complete(state, WorkflowStep.GENERATING_PRESENTATION, started_at)

        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | PRESENTATION | FAILED | {e}")
        return mark_failed(state, f"Presentation generation failed: {e}")
