"""Skill registry that scans, indexes, and loads agent skills.

Skills are markdown files (SKILL.md) with YAML frontmatter containing
metadata (name, description, triggers) and a body with full instructions.

The registry implements progressive disclosure:
1. list_skills() → lightweight name + description for LLM tool selection
2. load_skill(name) → full skill content loaded on-demand
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Default skills directory (sibling to app/ in backend/)
DEFAULT_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


@dataclass
class SkillInfo:
    """Lightweight skill metadata for progressive disclosure.

    Only name + description are exposed to the LLM initially,
    so it can decide which skills to load without consuming
    the full instruction content.
    """

    name: str
    description: str
    triggers: dict = field(default_factory=dict)
    path: Path = field(default_factory=lambda: Path("."))


@dataclass
class LoadedSkill:
    """A fully loaded skill with complete instructions."""

    name: str
    description: str
    content: str  # Full markdown body (instructions)
    triggers: dict = field(default_factory=dict)


class SkillRegistry:
    """Registry that discovers, indexes, and serves agent skills.

    Scans a directory for SKILL.md files, parses YAML frontmatter,
    and provides both lightweight listings and full content loading.

    Usage:
        registry = SkillRegistry()
        registry.scan()  # Discover all skills

        # Progressive disclosure
        infos = registry.list_skills()  # Names + descriptions only
        skill = registry.load_skill("excel_data_analysis")  # Full content
    """

    def __init__(self, skills_dir: Optional[Path] = None) -> None:
        self._skills_dir = skills_dir or DEFAULT_SKILLS_DIR
        self._index: dict[str, SkillInfo] = {}
        self._scanned = False

    @property
    def skills_dir(self) -> Path:
        return self._skills_dir

    def scan(self) -> int:
        """Scan the skills directory and build the index.

        Returns:
            Number of skills discovered
        """
        self._index.clear()

        if not self._skills_dir.exists():
            logger.warning(f"Skills directory not found: {self._skills_dir}")
            self._scanned = True
            return 0

        for skill_file in self._skills_dir.rglob("SKILL.md"):
            try:
                info = self._parse_frontmatter(skill_file)
                if info:
                    self._index[info.name] = info
                    logger.debug(f"Indexed skill: {info.name}")
            except Exception as e:
                logger.warning(f"Failed to index skill at {skill_file}: {e}")

        self._scanned = True
        logger.info(f"Skill registry scanned: {len(self._index)} skills found")
        return len(self._index)

    def _parse_frontmatter(self, path: Path) -> Optional[SkillInfo]:
        """Parse YAML frontmatter from a SKILL.md file.

        Expected format:
            ---
            name: skill_name
            description: Short description
            triggers:
              file_types: [".xlsx"]
            ---
            # Full instructions body...

        Args:
            path: Path to SKILL.md file

        Returns:
            SkillInfo with metadata, or None if invalid
        """
        text = path.read_text(encoding="utf-8")

        if not text.startswith("---"):
            logger.warning(f"Skill file missing frontmatter: {path}")
            return None

        # Split frontmatter from body
        parts = text.split("---", 2)
        if len(parts) < 3:
            logger.warning(f"Invalid frontmatter format: {path}")
            return None

        try:
            meta = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            logger.warning(f"Invalid YAML in {path}: {e}")
            return None

        if not meta or "name" not in meta:
            logger.warning(f"Skill missing 'name' field: {path}")
            return None

        return SkillInfo(
            name=meta["name"],
            description=meta.get("description", "").strip(),
            triggers=meta.get("triggers", {}),
            path=path,
        )

    def list_skills(self) -> list[SkillInfo]:
        """List all available skills (lightweight metadata only).

        Returns:
            List of SkillInfo with name, description, and triggers
        """
        if not self._scanned:
            self.scan()
        return list(self._index.values())

    def load_skill(self, name: str) -> Optional[LoadedSkill]:
        """Load the full content of a skill by name.

        Args:
            name: Skill name (from frontmatter)

        Returns:
            LoadedSkill with full instructions, or None if not found
        """
        if not self._scanned:
            self.scan()

        info = self._index.get(name)
        if not info:
            logger.warning(f"Skill not found: {name}")
            return None

        try:
            text = info.path.read_text(encoding="utf-8")
            # Extract body (after second ---)
            parts = text.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else ""

            return LoadedSkill(
                name=info.name,
                description=info.description,
                content=body,
                triggers=info.triggers,
            )
        except Exception as e:
            logger.error(f"Failed to load skill '{name}': {e}")
            return None

    def get_skills_for_file_types(self, file_types: set[str]) -> list[SkillInfo]:
        """Get skills relevant to specific file types.

        Args:
            file_types: Set of file extensions (e.g., {".xlsx", ".pdf"})

        Returns:
            List of matching SkillInfo objects
        """
        if not self._scanned:
            self.scan()

        matching = []
        for info in self._index.values():
            trigger_types = set(info.triggers.get("file_types", []))
            if trigger_types & file_types:
                matching.append(info)
        return matching

    def get_skills_for_output_formats(self, output_formats: list[str]) -> list[SkillInfo]:
        """Get skills relevant to specific output formats.

        Args:
            output_formats: List of output formats (e.g., ["pdf", "pptx"])

        Returns:
            List of matching SkillInfo objects
        """
        if not self._scanned:
            self.scan()

        matching = []
        for info in self._index.values():
            trigger_formats = set(info.triggers.get("output_formats", []))
            if trigger_formats & set(output_formats):
                matching.append(info)
        return matching

    def get_relevant_skills(
        self,
        file_types: set[str],
        output_formats: list[str],
    ) -> list[SkillInfo]:
        """Get all skills relevant to the current workflow context.

        Combines file type and output format matching, deduplicating results.

        Args:
            file_types: Set of input file extensions
            output_formats: List of requested output formats

        Returns:
            Deduplicated list of relevant SkillInfo objects
        """
        seen = set()
        result = []

        for info in self.get_skills_for_file_types(file_types):
            if info.name not in seen:
                seen.add(info.name)
                result.append(info)

        for info in self.get_skills_for_output_formats(output_formats):
            if info.name not in seen:
                seen.add(info.name)
                result.append(info)

        return result


# Singleton registry instance
_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get the singleton skill registry, scanning on first access.

    Returns:
        Initialized SkillRegistry
    """
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        _registry.scan()
    return _registry
