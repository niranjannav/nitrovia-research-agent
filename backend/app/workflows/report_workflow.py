"""LangGraph workflow for report generation.

Defines the state graph that orchestrates the full report generation pipeline.
Uses an agent-based research approach: files are registered (metadata only),
then a research agent selectively reads and analyzes them using tools.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from langgraph.graph import END, StateGraph

from app.services.supabase import get_supabase_client
from app.workflows.nodes.register_files import register_files_node
from app.workflows.nodes.plan_skills import plan_skills_node
from app.workflows.nodes.research_agent import research_agent_node
from app.workflows.nodes.generate_report import generate_report_node
from app.workflows.nodes.generate_presentation import generate_presentation_node
from app.workflows.nodes.render_outputs import render_outputs_node
from app.workflows.state import (
    ReportWorkflowState,
    WorkflowStep,
    create_initial_state,
    mark_step_complete,
    update_progress,
)

logger = logging.getLogger(__name__)


def finalize_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Finalize the workflow and save results to database.

    Updates the report record with generated content, output files,
    and completion status.

    Args:
        state: Current workflow state

    Returns:
        Final workflow state
    """
    report_id = state["report_id"]
    started_at = datetime.utcnow()

    logger.info(f"[WORKFLOW] Report {report_id} | FINALIZE | Saving results...")

    state = update_progress(
        state,
        WorkflowStep.FINALIZING,
        98,
        "Finalizing report...",
    )

    try:
        supabase = get_supabase_client()

        # Calculate generation time
        workflow_started = state.get("started_at")
        generation_time = 0
        if workflow_started:
            generation_time = int((datetime.utcnow() - workflow_started).total_seconds())

        # Get generated content
        generated_report = state.get("generated_report")
        generated_presentation = state.get("generated_presentation")
        output_files = state.get("output_files", [])
        token_metrics = state.get("token_metrics")

        # Convert output files to dict format
        output_files_dict = [
            {
                "format": f.format,
                "storage_path": f.storage_path,
                "download_url": f.download_url,
                "expires_at": f.expires_at,
            }
            for f in output_files
        ]

        # Update report in database
        update_data = {
            "status": "completed",
            "progress": 100,
            "generated_content": {
                "report": generated_report.model_dump() if generated_report else None,
                "presentation": generated_presentation.model_dump() if generated_presentation else None,
            },
            "output_files": output_files_dict,
            "total_input_tokens": token_metrics.total_input_tokens if token_metrics else 0,
            "total_output_tokens": token_metrics.total_output_tokens if token_metrics else 0,
            "generation_time_seconds": generation_time,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "title": generated_report.title if generated_report else None,
        }

        supabase.table("reports").update(update_data).eq("id", report_id).execute()

        # Log completion
        try:
            supabase.table("generation_logs").insert({
                "report_id": report_id,
                "step": "completed",
                "status": "completed",
                "message": f"Report completed in {generation_time}s",
            }).execute()
        except Exception:
            pass

        logger.info(
            f"[WORKFLOW] Report {report_id} | FINALIZE | COMPLETED | "
            f"time={generation_time}s, files={len(output_files)}"
        )

        # Update final state
        state = {
            **state,
            "current_step": WorkflowStep.COMPLETED,
            "progress": 100,
            "status_message": "Report completed",
            "completed_at": datetime.utcnow(),
        }

        state = mark_step_complete(state, WorkflowStep.FINALIZING, started_at)

        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | FINALIZE | FAILED | {e}")
        # Don't mark as failed here - report was generated, just finalization had issues
        state = {
            **state,
            "current_step": WorkflowStep.COMPLETED,
            "progress": 100,
        }
        return state


def handle_error_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Handle workflow errors.

    Updates the database with error status when the workflow fails.

    Args:
        state: Current workflow state (failed)

    Returns:
        Final failed state
    """
    report_id = state["report_id"]
    errors = state.get("errors", [])
    error_message = errors[-1] if errors else "Unknown error"

    logger.error(f"[WORKFLOW] Report {report_id} | ERROR | {error_message}")

    try:
        supabase = get_supabase_client()

        supabase.table("reports").update({
            "status": "failed",
            "progress": 0,
            "error_message": error_message,
        }).eq("id", report_id).execute()

        try:
            supabase.table("generation_logs").insert({
                "report_id": report_id,
                "step": "error",
                "status": "failed",
                "message": error_message,
            }).execute()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | ERROR | Failed to update DB: {e}")

    return state


def should_continue(state: ReportWorkflowState) -> str:
    """Determine next step based on state.

    Checks if workflow has failed and routes accordingly.

    Args:
        state: Current workflow state

    Returns:
        Next node name or END
    """
    if state.get("failed"):
        return "handle_error"
    return "continue"


def route_after_report(state: ReportWorkflowState) -> str:
    """Route after report generation.

    Determines whether to generate presentation or skip to rendering.

    Args:
        state: Current workflow state

    Returns:
        Next node name
    """
    if state.get("failed"):
        return "handle_error"

    config = state.get("config", {})
    output_formats = config.get("output_formats", ["pdf"])

    if "pptx" in output_formats:
        return "generate_presentation"
    return "render_outputs"


def create_report_workflow() -> StateGraph:
    """Create the report generation workflow graph.

    New agent-based pipeline:
    1. Register files (metadata only, no upfront parsing)
    2. Plan skills (load only relevant skills based on file types)
    3. Research agent (selectively reads files with tools, collects material)
    4. Report generation (uses research notes)
    5. Presentation generation (conditional, if PPTX requested)
    6. Output rendering (PDF, DOCX, PPTX)
    7. Finalization (save to database)

    Returns:
        Compiled StateGraph workflow
    """
    # Create workflow graph
    workflow = StateGraph(ReportWorkflowState)

    # Add nodes
    workflow.add_node("register_files", register_files_node)
    workflow.add_node("plan_skills", plan_skills_node)
    workflow.add_node("research_agent", research_agent_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("generate_presentation", generate_presentation_node)
    workflow.add_node("render_outputs", render_outputs_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("handle_error", handle_error_node)

    # Set entry point
    workflow.set_entry_point("register_files")

    # register_files → plan_skills (or error)
    workflow.add_conditional_edges(
        "register_files",
        should_continue,
        {
            "continue": "plan_skills",
            "handle_error": "handle_error",
        },
    )

    # plan_skills → research_agent (or error)
    workflow.add_conditional_edges(
        "plan_skills",
        should_continue,
        {
            "continue": "research_agent",
            "handle_error": "handle_error",
        },
    )

    # research_agent → generate_report (or error)
    workflow.add_conditional_edges(
        "research_agent",
        should_continue,
        {
            "continue": "generate_report",
            "handle_error": "handle_error",
        },
    )

    # After report, conditionally route to presentation or rendering
    workflow.add_conditional_edges(
        "generate_report",
        route_after_report,
        {
            "generate_presentation": "generate_presentation",
            "render_outputs": "render_outputs",
            "handle_error": "handle_error",
        },
    )

    workflow.add_conditional_edges(
        "generate_presentation",
        should_continue,
        {
            "continue": "render_outputs",
            "handle_error": "handle_error",
        },
    )

    workflow.add_conditional_edges(
        "render_outputs",
        should_continue,
        {
            "continue": "finalize",
            "handle_error": "handle_error",
        },
    )

    # Final edges
    workflow.add_edge("finalize", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()


# Singleton workflow instance
_workflow: Optional[StateGraph] = None


def get_report_workflow() -> StateGraph:
    """Get the singleton report workflow instance.

    Returns:
        Compiled report workflow
    """
    global _workflow
    if _workflow is None:
        _workflow = create_report_workflow()
    return _workflow


async def run_report_workflow(
    report_id: str,
    user_id: str,
    config: dict[str, Any],
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> ReportWorkflowState:
    """Run the report generation workflow.

    Convenience function to execute the workflow with initial state.

    Args:
        report_id: Report UUID
        user_id: User UUID
        config: Report configuration
        on_progress: Optional callback for progress updates

    Returns:
        Final workflow state
    """
    logger.info(f"[WORKFLOW] Report {report_id} | STARTED | Beginning workflow execution")

    # Create initial state
    initial_state = create_initial_state(report_id, user_id, config)

    # Log start
    try:
        supabase = get_supabase_client()
        supabase.table("reports").update({
            "status": "processing",
            "progress": 5,
        }).eq("id", report_id).execute()

        supabase.table("generation_logs").insert({
            "report_id": report_id,
            "step": "started",
            "status": "started",
            "message": "Report generation started",
        }).execute()
    except Exception as e:
        logger.warning(f"[WORKFLOW] Report {report_id} | Failed to log start: {e}")

    # Get workflow
    workflow = get_report_workflow()

    # Execute workflow asynchronously
    final_state = await workflow.ainvoke(initial_state)

    logger.info(
        f"[WORKFLOW] Report {report_id} | FINISHED | "
        f"status={final_state.get('current_step')}, "
        f"failed={final_state.get('failed')}"
    )

    return final_state
