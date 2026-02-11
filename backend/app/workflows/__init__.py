"""LangGraph workflows for report generation.

This module provides stateful, observable workflows for complex
multi-step operations like report generation.

Example usage:
    from app.workflows import run_report_workflow

    # Run the report generation workflow
    final_state = await run_report_workflow(
        report_id="...",
        user_id="...",
        config={"detail_level": "standard", "output_formats": ["pdf", "pptx"]},
    )

    if final_state["failed"]:
        print(f"Error: {final_state['errors']}")
    else:
        print(f"Report generated: {final_state['generated_report'].title}")
"""

from .report_workflow import (
    create_report_workflow,
    get_report_workflow,
    run_report_workflow,
)
from .state import (
    DocumentContext,
    OutputFile,
    PreparedContext,
    ReportWorkflowState,
    StepTiming,
    TokenMetrics,
    WorkflowStep,
    create_initial_state,
)

__all__ = [
    # Workflow
    "create_report_workflow",
    "get_report_workflow",
    "run_report_workflow",
    # State
    "ReportWorkflowState",
    "WorkflowStep",
    "DocumentContext",
    "PreparedContext",
    "OutputFile",
    "TokenMetrics",
    "StepTiming",
    "create_initial_state",
]
