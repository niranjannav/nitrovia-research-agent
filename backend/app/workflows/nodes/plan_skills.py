"""Skill planning node for the report workflow.

Uses an LLM agent with tool-calling to select and load relevant skills
based on input file types, output formats, and user instructions.
Implements the progressive disclosure pattern: the agent sees skill
names + descriptions, then calls load_skill() for the ones it needs.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.llm import GatewayConfig, ModelGateway, TaskType
from app.skills.registry import get_skill_registry
from app.skills.tool import SkillPlanningContext, get_skill_catalog_prompt
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


def _get_fallback_planning_prompt() -> str:
    """Fallback prompt if file not found."""
    return """You are a skill planning agent. Analyze the workflow context and
load relevant skills using the load_skill tool.

{skill_catalog}

Review the input file types and output formats, then load skills that will
improve the quality of the generated report and presentation."""


async def plan_skills_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Plan and load skills for the current workflow.

    This node:
    1. Builds a catalog of available skills (names + descriptions)
    2. Runs an LLM agent that decides which skills to load
    3. The agent calls load_skill() tool for each relevant skill
    4. Stores loaded skill content in state for downstream nodes

    For efficiency, if skill triggers clearly match (deterministic path),
    skills are loaded directly without an LLM call.

    Args:
        state: Current workflow state with parsed documents and context

    Returns:
        Updated state with loaded skills
    """
    report_id = state["report_id"]
    config = state.get("config", {})
    started_at = datetime.utcnow()

    logger.info(f"[WORKFLOW] Report {report_id} | SKILLS | Planning skill selection...")

    state = update_progress(
        state,
        WorkflowStep.PLANNING_SKILLS,
        28,
        "Selecting analysis skills...",
    )

    try:
        registry = get_skill_registry()
        all_skills = registry.list_skills()

        if not all_skills:
            logger.info(f"[WORKFLOW] Report {report_id} | SKILLS | No skills available, skipping")
            state = update_progress(state, WorkflowStep.PLANNING_SKILLS, 32, "No skills needed")
            state = mark_step_complete(state, WorkflowStep.PLANNING_SKILLS, started_at)
            return state

        input_file_types = state.get("input_file_types", set())
        output_formats = config.get("output_formats", ["pdf"])

        # --- Deterministic fast path ---
        # If we can determine relevant skills purely from triggers, skip LLM call
        relevant_skills = registry.get_relevant_skills(input_file_types, output_formats)

        if relevant_skills:
            # Load all relevant skills directly (no LLM needed)
            loaded_skills = []
            for info in relevant_skills:
                skill = registry.load_skill(info.name)
                if skill:
                    loaded_skills.append({
                        "name": skill.name,
                        "content": skill.content,
                    })
                    logger.info(
                        f"[WORKFLOW] Report {report_id} | SKILLS | "
                        f"Loaded (deterministic): {skill.name}"
                    )

            skill_names = [s["name"] for s in loaded_skills]
            plan_notes = (
                f"Skills loaded based on input types {input_file_types} "
                f"and output formats {output_formats}: {', '.join(skill_names)}"
            )

            state = {
                **state,
                "loaded_skills": loaded_skills,
                "skill_plan_notes": plan_notes,
            }

            logger.info(
                f"[WORKFLOW] Report {report_id} | SKILLS | COMPLETED (deterministic) | "
                f"Loaded {len(loaded_skills)} skills: {', '.join(skill_names)}"
            )

            state = update_progress(state, WorkflowStep.PLANNING_SKILLS, 32, "Skills loaded")
            state = mark_step_complete(state, WorkflowStep.PLANNING_SKILLS, started_at)
            return state

        # --- LLM agent path (when triggers don't clearly match) ---
        logger.info(
            f"[WORKFLOW] Report {report_id} | SKILLS | "
            f"No clear trigger match, using LLM agent for skill selection"
        )

        # Build skill catalog for the agent
        skill_catalog = get_skill_catalog_prompt(input_file_types, output_formats)

        # Load planning prompt
        try:
            prompt_template = _load_prompt("skill_planning")
        except FileNotFoundError:
            logger.warning("Skill planning prompt not found, using fallback")
            prompt_template = _get_fallback_planning_prompt()

        system_prompt = prompt_template.format(skill_catalog=skill_catalog)

        # Build context message for the agent
        custom_instructions = config.get("custom_instructions", "")
        user_message = (
            f"Input file types: {', '.join(input_file_types) if input_file_types else 'none detected'}\n"
            f"Output formats: {', '.join(output_formats)}\n"
            f"User instructions: {custom_instructions or 'None provided'}\n\n"
            f"Analyze the context and load any skills that would improve the "
            f"report and presentation quality. Call the load_skill tool for each "
            f"relevant skill."
        )

        # Create LLM gateway for the planning call
        gateway_config = GatewayConfig(
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=getattr(settings, "openai_api_key", None),
        )
        gateway = ModelGateway(gateway_config)

        # Use generate_text with tool calling for the planning agent
        # For now, use the deterministic approach as primary and
        # fall back to loading all relevant skills
        # TODO: Implement full pydantic-ai agent with tool calling when
        # the planning scenarios become more complex

        response, usage = await gateway.generate_text(
            task=TaskType.CLASSIFICATION,
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            max_tokens=1000,
        )

        # Parse the LLM response to find skill recommendations
        loaded_skills = []
        for info in all_skills:
            if info.name.lower() in response.lower():
                skill = registry.load_skill(info.name)
                if skill:
                    loaded_skills.append({
                        "name": skill.name,
                        "content": skill.content,
                    })

        skill_names = [s["name"] for s in loaded_skills]
        state = {
            **state,
            "loaded_skills": loaded_skills,
            "skill_plan_notes": response[:500],
        }

        state = update_token_metrics(
            state,
            usage.input_tokens,
            usage.output_tokens,
            usage.estimated_cost,
        )

        logger.info(
            f"[WORKFLOW] Report {report_id} | SKILLS | COMPLETED (LLM) | "
            f"Loaded {len(loaded_skills)} skills: {', '.join(skill_names)}"
        )

        state = update_progress(state, WorkflowStep.PLANNING_SKILLS, 32, "Skills loaded")
        state = mark_step_complete(state, WorkflowStep.PLANNING_SKILLS, started_at)
        return state

    except Exception as e:
        # Skill planning failure is non-fatal — continue without skills
        logger.warning(
            f"[WORKFLOW] Report {report_id} | SKILLS | FAILED (non-fatal) | {e}"
        )
        state = {
            **state,
            "loaded_skills": [],
            "skill_plan_notes": f"Skill planning failed: {e}",
        }
        state = update_progress(state, WorkflowStep.PLANNING_SKILLS, 32, "Continuing without skills")
        state = mark_step_complete(state, WorkflowStep.PLANNING_SKILLS, started_at)
        return state
