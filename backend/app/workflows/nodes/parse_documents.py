"""Parse documents node for the report workflow.

Downloads and parses source documents for the report.
"""

import logging
from datetime import datetime

from app.config import get_settings
from app.services.document_parser import ParserFactory
from app.services.supabase import get_supabase_client
from app.workflows.state import (
    ReportWorkflowState,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def parse_documents_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Parse source documents for the report.

    Downloads files from storage and parses them into text content.
    Reuses cached parsed content when available.

    Args:
        state: Current workflow state

    Returns:
        Updated state with parsed documents
    """
    report_id = state["report_id"]
    started_at = datetime.utcnow()

    logger.info(f"[WORKFLOW] Report {report_id} | PARSING | Starting document parsing...")

    state = update_progress(
        state,
        WorkflowStep.PARSING,
        10,
        "Parsing source documents...",
    )

    try:
        supabase = get_supabase_client()

        # Get the report to find source file IDs
        report = supabase.table("reports").select("source_files").eq(
            "id", report_id
        ).single().execute()

        if not report.data or not report.data.get("source_files"):
            return mark_failed(state, "No source files found for report")

        # Extract file IDs
        source_file_ids = [sf["id"] for sf in report.data["source_files"]]
        logger.info(f"[WORKFLOW] Report {report_id} | PARSING | Found {len(source_file_ids)} source files")

        # Fetch all source files
        source_files = supabase.table("source_files").select("*").in_(
            "id", source_file_ids
        ).execute()

        documents: list[tuple[str, str]] = []

        for sf in source_files.data:
            file_name = sf.get("file_name", "unknown")
            try:
                # Check if already parsed (reuse cached content)
                if sf.get("parsing_status") == "completed" and sf.get("parsed_content"):
                    logger.info(f"[WORKFLOW] Report {report_id} | PARSING | Reusing cached: {file_name}")
                    parsed_content = sf["parsed_content"]
                else:
                    # Download file from storage
                    storage_path = sf.get("storage_path")
                    if not storage_path:
                        logger.warning(f"[WORKFLOW] Report {report_id} | PARSING | No storage path for: {file_name}")
                        continue

                    logger.info(f"[WORKFLOW] Report {report_id} | PARSING | Downloading: {file_name}")
                    file_content = supabase.storage.from_(
                        settings.upload_bucket
                    ).download(storage_path)

                    # Parse file
                    file_type = sf.get("file_type", "")
                    parsed_content = ParserFactory.parse_file(file_content, file_type)

                    # Cache parsed content
                    try:
                        supabase.table("source_files").update({
                            "parsed_content": parsed_content,
                            "parsing_status": "completed",
                        }).eq("id", sf["id"]).execute()
                    except Exception as cache_error:
                        logger.warning(f"[WORKFLOW] Report {report_id} | PARSING | Cache update failed: {cache_error}")

                    logger.info(f"[WORKFLOW] Report {report_id} | PARSING | Parsed: {file_name} ({len(parsed_content)} chars)")

                documents.append((file_name, parsed_content))

            except Exception as e:
                logger.error(f"[WORKFLOW] Report {report_id} | PARSING | Failed to parse {file_name}: {e}")
                try:
                    supabase.table("source_files").update({
                        "parsing_status": "failed",
                        "parsing_error": str(e)[:500],
                    }).eq("id", sf["id"]).execute()
                except Exception:
                    pass

        if not documents:
            return mark_failed(state, "No documents could be parsed")

        logger.info(f"[WORKFLOW] Report {report_id} | PARSING | COMPLETED | Parsed {len(documents)} documents")

        # Update state
        state = {
            **state,
            "documents": documents,
        }

        state = update_progress(state, WorkflowStep.PARSING, 20, "Documents parsed")
        state = mark_step_complete(state, WorkflowStep.PARSING, started_at)

        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | PARSING | FAILED | {e}")
        return mark_failed(state, f"Document parsing failed: {e}")
