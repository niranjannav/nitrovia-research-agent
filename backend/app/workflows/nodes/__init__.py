"""Workflow nodes for report generation.

Each node represents a step in the report generation pipeline.
Nodes receive the workflow state, perform their task, and return
updated state.

Pipeline:
  parse_documents → index_documents → retrieve_context → [build_context] →
  generate_report → [generate_presentation] → render_outputs → finalize
"""

from .build_context import build_context_node
from .generate_presentation import generate_presentation_node
from .generate_report import generate_report_node
from .index_documents import index_documents_node
from .parse_documents import parse_documents_node
from .render_outputs import render_outputs_node
from .retrieve_context import retrieve_context_node

__all__ = [
    "parse_documents_node",
    "index_documents_node",
    "retrieve_context_node",
    "build_context_node",
    "generate_report_node",
    "generate_presentation_node",
    "render_outputs_node",
]
