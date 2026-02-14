"""Workflow nodes for report generation.

Each node represents a step in the report generation pipeline.
Nodes receive the workflow state, perform their task, and return
updated state.

New pipeline:
  register_files → research_agent → generate_report → [generate_presentation] → render_outputs

Legacy nodes (parse_documents, build_context, plan_skills) are kept
for backward compatibility but no longer used in the main workflow.
"""

from .generate_presentation import generate_presentation_node
from .generate_report import generate_report_node
from .register_files import register_files_node
from .render_outputs import render_outputs_node
from .research_agent import research_agent_node

# Legacy imports (kept for backward compat)
from .build_context import build_context_node
from .parse_documents import parse_documents_node
from .plan_skills import plan_skills_node

__all__ = [
    # New pipeline
    "register_files_node",
    "research_agent_node",
    "generate_report_node",
    "generate_presentation_node",
    "render_outputs_node",
    # Legacy
    "parse_documents_node",
    "build_context_node",
    "plan_skills_node",
]
