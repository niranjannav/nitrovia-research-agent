"""Agent Skills package.

Provides a registry for loading and managing Anthropic-style
agent skills with progressive disclosure via tool calling.
"""

from app.skills.registry import LoadedSkill, SkillInfo, SkillRegistry

__all__ = [
    "SkillRegistry",
    "SkillInfo",
    "LoadedSkill",
]
