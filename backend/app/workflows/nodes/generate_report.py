"""Generate report node for the report workflow.

Uses the LLM gateway to generate the report content.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.llm import GatewayConfig, ModelGateway, TaskType
from app.models.llm_outputs import LLMGeneratedReport
from app.models.schemas import GeneratedReport, ReportSection
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


def _get_detail_guidance(detail_level: str) -> str:
    """Get the detail guidance for a specific level."""
    try:
        detail_content = _load_prompt("detail_levels")
        sections = detail_content.split("## ")
        for section in sections:
            if section.startswith(detail_level):
                lines = section.strip().split("\n", 1)
                if len(lines) > 1:
                    return lines[1].strip()
    except Exception as e:
        logger.warning(f"Failed to load detail guidance: {e}")

    fallbacks = {
        "executive": "Create a concise executive summary report (1-2 pages equivalent). Focus on key takeaways and actionable recommendations.",
        "standard": "Create a balanced report (3-5 pages equivalent). Include executive summary, analysis, and recommendations.",
        "comprehensive": "Create an in-depth analytical report (5-10 pages equivalent). Provide thorough analysis with detailed findings.",
    }
    return fallbacks.get(detail_level, fallbacks["standard"])


def _get_fallback_report_prompt() -> str:
    """Fallback prompt if file not found."""
    return """You are an expert research analyst. Create a professional report.

REPORT TITLE: {title}
DETAIL LEVEL: {detail_level}
{detail_guidance}

Create a comprehensive report with an executive summary (2-3 paragraphs),
detailed sections with substantive content, at least 2 key findings,
and at least 1 actionable recommendation."""


def _convert_llm_report_to_schema(llm_report: LLMGeneratedReport) -> GeneratedReport:
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
                        subsections=[],
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


async def generate_report_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Generate report content using the LLM gateway.

    Uses structured output to generate a validated report. Consumes
    research_notes from the research agent (preferred) or falls back
    to prepared_context for backward compatibility.

    Args:
        state: Current workflow state with research_notes or prepared_context

    Returns:
        Updated state with generated report
    """
    report_id = state["report_id"]
    config = state.get("config", {})
    research_notes = state.get("research_notes", "")
    prepared_context = state.get("prepared_context")
    started_at = datetime.utcnow()

    logger.info(f"[WORKFLOW] Report {report_id} | REPORT | Generating report content...")

    state = update_progress(
        state,
        WorkflowStep.GENERATING_REPORT,
        55,
        "Generating report content...",
    )

    # Determine content source
    if research_notes:
        source_content = research_notes
        logger.info(f"[WORKFLOW] Report {report_id} | REPORT | Using research notes ({len(research_notes)} chars)")
    elif prepared_context:
        source_content = prepared_context.combined_content
        logger.info(f"[WORKFLOW] Report {report_id} | REPORT | Using prepared context (legacy)")
    else:
        return mark_failed(state, "No research notes or context available")

    try:
        # Create gateway
        gateway_config = GatewayConfig(
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=getattr(settings, "openai_api_key", None),
        )
        gateway = ModelGateway(gateway_config)

        # Load prompt template
        try:
            prompt_template = _load_prompt("report_generation")
        except FileNotFoundError:
            logger.warning("Report generation prompt not found, using fallback")
            prompt_template = _get_fallback_report_prompt()

        # Get detail guidance
        detail_level = config.get("detail_level", "standard")
        detail_guidance = _get_detail_guidance(detail_level)

        # Build system prompt
        title = config.get("title", "Research Report")
        system_prompt = prompt_template.format(
            title=title,
            detail_level=detail_level.upper(),
            detail_guidance=detail_guidance,
        )

        # Build user content
        user_content = ""
        custom_instructions = config.get("custom_instructions")
        if custom_instructions:
            user_content += f"USER INSTRUCTIONS:\n{custom_instructions}\n\n"

        user_content += f"RESEARCH MATERIAL:\n{source_content}\n\nGenerate the report now."

        logger.info(f"[WORKFLOW] Report {report_id} | REPORT | Calling LLM with detail_level={detail_level}")

        # Generate structured output
        llm_report, usage = await gateway.generate_structured(
            task=TaskType.REPORT_GENERATION,
            output_schema=LLMGeneratedReport,
            messages=[{"role": "user", "content": user_content}],
            system_prompt=system_prompt,
            max_tokens=8000,
        )

        # Convert to API schema
        generated_report = _convert_llm_report_to_schema(llm_report)

        logger.info(
            f"[WORKFLOW] Report {report_id} | REPORT | COMPLETED | "
            f"title={generated_report.title}, "
            f"sections={len(generated_report.sections)}, "
            f"findings={len(generated_report.key_findings)}"
        )

        # Update state
        state = {
            **state,
            "generated_report": generated_report,
        }

        state = update_token_metrics(
            state,
            usage.input_tokens,
            usage.output_tokens,
            usage.estimated_cost,
        )
        state = update_progress(state, WorkflowStep.GENERATING_REPORT, 60, "Report generated")
        state = mark_step_complete(state, WorkflowStep.GENERATING_REPORT, started_at)

        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | REPORT | FAILED | {e}")
        return mark_failed(state, f"Report generation failed: {e}")
