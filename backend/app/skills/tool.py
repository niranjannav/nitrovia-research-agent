"""Pydantic-AI tool wrapper for skill loading.

Provides the `load_skill` tool that an LLM agent can call
to load full skill instructions during the planning phase.
This implements the progressive disclosure pattern.
"""

import logging
from dataclasses import dataclass

from pydantic_ai import RunContext

from app.skills.registry import LoadedSkill, SkillRegistry, get_skill_registry

logger = logging.getLogger(__name__)


@dataclass
class SkillPlanningContext:
    """Context passed to the skill planning agent.

    Contains everything the agent needs to decide which skills to load
    and how to apply them.
    """

    input_file_types: set[str]
    output_formats: list[str]
    custom_instructions: str | None = None
    registry: SkillRegistry | None = None

    @property
    def _registry(self) -> SkillRegistry:
        return self.registry or get_skill_registry()


def create_load_skill_tool():
    """Create the load_skill tool function for pydantic-ai agents.

    Returns a tool function that can be registered with a pydantic-ai Agent.
    The tool loads full skill content by name, implementing progressive disclosure.

    Returns:
        Async tool function compatible with pydantic-ai
    """

    async def load_skill(
        ctx: RunContext[SkillPlanningContext],
        skill_name: str,
    ) -> str:
        """Load the full instructions for a specific skill.

        Call this tool to retrieve detailed instructions for a skill
        that is relevant to the current task. Only load skills you
        intend to use — each loaded skill's guidance will be injected
        into subsequent generation steps.

        Args:
            skill_name: The exact name of the skill to load (from the available skills list)

        Returns:
            Full skill instructions as markdown text, or an error message
        """
        registry = ctx.deps._registry

        skill = registry.load_skill(skill_name)
        if skill is None:
            available = [s.name for s in registry.list_skills()]
            return (
                f"Skill '{skill_name}' not found. "
                f"Available skills: {', '.join(available)}"
            )

        logger.info(f"Skill loaded by agent: {skill_name} ({len(skill.content)} chars)")
        return skill.content

    return load_skill


def get_skill_catalog_prompt(
    file_types: set[str],
    output_formats: list[str],
) -> str:
    """Build a skill catalog prompt for the LLM.

    Creates a formatted list of available skills with names and descriptions,
    highlighting which skills are most relevant based on context.

    Args:
        file_types: Input file types in the workflow
        output_formats: Requested output formats

    Returns:
        Formatted skill catalog string for inclusion in system prompts
    """
    registry = get_skill_registry()
    all_skills = registry.list_skills()

    if not all_skills:
        return ""

    relevant = registry.get_relevant_skills(file_types, output_formats)
    relevant_names = {s.name for s in relevant}

    lines = ["## Available Skills", ""]
    lines.append(
        "The following skills are available. Use the `load_skill` tool to "
        "load full instructions for any skill you want to apply."
    )
    lines.append("")

    for info in all_skills:
        marker = " ⭐ (recommended)" if info.name in relevant_names else ""
        lines.append(f"- **{info.name}**{marker}: {info.description}")

    lines.append("")
    lines.append(
        "Load skills that match the input file types and requested output formats. "
        "Each loaded skill provides specialized instructions that improve quality."
    )

    return "\n".join(lines)
