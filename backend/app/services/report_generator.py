"""Report generation orchestration service.

This module provides the main entry point for report generation.
Uses LangGraph workflow for robust, stateful execution.
"""

import logging
import traceback

from app.config import get_settings
from app.services.supabase import get_supabase_client
from app.workflows import run_report_workflow

logger = logging.getLogger(__name__)
settings = get_settings()


class ReportGeneratorService:
    """Orchestrates the full report generation pipeline.

    Uses LangGraph workflow for stateful, observable execution with
    automatic error handling and retry support.
    """

    def __init__(self):
        """Initialize the service."""
        self.supabase = get_supabase_client()

    async def generate(self, report_id: str, user_id: str) -> None:
        """
        Execute full report generation pipeline using LangGraph workflow.

        The workflow handles:
        1. Document parsing
        2. Context building (with summarization)
        3. Report generation via LLM
        4. Presentation generation (if PPTX requested)
        5. Output rendering (PDF, DOCX, PPTX)
        6. Finalization and database update

        Args:
            report_id: Report UUID
            user_id: User UUID

        Raises:
            ValueError: If report not found or generation fails
        """
        logger.info(f"[WORKFLOW] Report {report_id} | STARTED | Beginning LangGraph workflow")

        try:
            # Get report configuration
            report = self.supabase.table("reports").select("*").eq(
                "id", report_id
            ).single().execute()

            if not report.data:
                raise ValueError(f"Report not found: {report_id}")

            report_config = report.data

            # Run the LangGraph workflow
            final_state = await run_report_workflow(
                report_id=report_id,
                user_id=user_id,
                config=report_config,
            )

            # Check for workflow failure
            if final_state.get("failed"):
                errors = final_state.get("errors", [])
                error_msg = errors[-1] if errors else "Unknown workflow error"
                raise ValueError(error_msg)

            logger.info(f"[WORKFLOW] Report {report_id} | FINISHED | Workflow completed successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[WORKFLOW] Report {report_id} | FAILED | Error: {error_msg}")
            logger.error(f"[WORKFLOW] Report {report_id} | TRACEBACK | {traceback.format_exc()}")

            # Update status in database
            try:
                self.supabase.table("reports").update({
                    "status": "failed",
                    "progress": 0,
                    "error_message": error_msg,
                }).eq("id", report_id).execute()
            except Exception:
                pass

            raise
