"""Render outputs node for the report workflow.

Renders the generated report and presentation to various output formats.
"""

import logging
import traceback
from datetime import datetime, timezone

from app.config import get_settings
from app.services.docx_renderer import DOCXRenderer
from app.services.pdf_renderer import PDFRenderer
from app.services.pptx_renderer import PPTXRenderer
from app.services.supabase import get_supabase_client
from app.workflows.state import (
    OutputFile,
    ReportWorkflowState,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def render_outputs_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Render generated content to output files.

    Renders PDF, DOCX, and PPTX as requested, uploads to storage,
    and generates signed download URLs.

    Args:
        state: Current workflow state with generated content

    Returns:
        Updated state with output files
    """
    report_id = state["report_id"]
    user_id = state["user_id"]
    config = state.get("config", {})
    generated_report = state.get("generated_report")
    generated_presentation = state.get("generated_presentation")
    started_at = datetime.utcnow()

    output_formats = config.get("output_formats", ["pdf"])

    logger.info(f"[WORKFLOW] Report {report_id} | RENDER | Rendering formats: {output_formats}")

    state = update_progress(
        state,
        WorkflowStep.RENDERING,
        82,
        "Rendering output files...",
    )

    if not generated_report:
        return mark_failed(state, "No report available for rendering")

    try:
        supabase = get_supabase_client()
        pdf_renderer = PDFRenderer()
        docx_renderer = DOCXRenderer()
        pptx_renderer = PPTXRenderer()

        output_files: list[OutputFile] = []

        for fmt in output_formats:
            try:
                logger.info(f"[WORKFLOW] Report {report_id} | RENDER | Rendering: {fmt}")

                if fmt == "pdf":
                    content = pdf_renderer.render(generated_report)
                    content_type = "application/pdf"
                    extension = "pdf"

                elif fmt == "docx":
                    content = docx_renderer.render(generated_report)
                    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    extension = "docx"

                elif fmt == "pptx" and generated_presentation:
                    content = pptx_renderer.render(generated_presentation)
                    content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    extension = "pptx"

                else:
                    logger.info(f"[WORKFLOW] Report {report_id} | RENDER | Skipping: {fmt}")
                    continue

                # Upload to storage
                storage_path = f"{user_id}/{report_id}/output.{extension}"
                logger.info(f"[WORKFLOW] Report {report_id} | RENDER | Uploading: {storage_path}")

                supabase.storage.from_(settings.output_bucket).upload(
                    storage_path,
                    content.getvalue(),
                    {"content-type": content_type},
                )

                # Generate signed URL for download (7 days)
                signed_url_response = supabase.storage.from_(
                    settings.output_bucket
                ).create_signed_url(storage_path, 3600 * 24 * 7)

                download_url = signed_url_response.get("signedUrl") or signed_url_response.get("signedURL")

                if not download_url:
                    logger.error(f"[WORKFLOW] Report {report_id} | RENDER | No signed URL: {signed_url_response}")

                output_files.append(
                    OutputFile(
                        format=fmt,
                        storage_path=storage_path,
                        download_url=download_url,
                        expires_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

                logger.info(f"[WORKFLOW] Report {report_id} | RENDER | COMPLETED | {fmt}")

            except Exception as e:
                logger.error(f"[WORKFLOW] Report {report_id} | RENDER | FAILED | {fmt}: {e}")
                logger.error(f"[WORKFLOW] Report {report_id} | TRACEBACK | {traceback.format_exc()}")

        if not output_files:
            return mark_failed(state, "Failed to render any output files")

        logger.info(f"[WORKFLOW] Report {report_id} | RENDER | ALL COMPLETED | {len(output_files)} files")

        # Update state
        state = {
            **state,
            "output_files": output_files,
        }

        state = update_progress(state, WorkflowStep.RENDERING, 95, "Files rendered")
        state = mark_step_complete(state, WorkflowStep.RENDERING, started_at)

        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | RENDER | FAILED | {e}")
        return mark_failed(state, f"Output rendering failed: {e}")
