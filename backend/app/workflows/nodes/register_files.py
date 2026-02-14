"""Register files node for the report workflow.

Registers uploaded file metadata without parsing content upfront.
The research agent will selectively read files on demand.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.services.supabase import get_supabase_client
from app.workflows.state import (
    FileRegistryEntry,
    ReportWorkflowState,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def register_files_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Register source files metadata without parsing.

    Fetches file metadata from Supabase and populates the file registry.
    No content is parsed at this stage — the research agent will read
    files on demand using its tools.

    Args:
        state: Current workflow state

    Returns:
        Updated state with file_registry populated
    """
    report_id = state["report_id"]
    started_at = datetime.utcnow()

    logger.info(f"[WORKFLOW] Report {report_id} | REGISTER_FILES | Registering source files...")

    state = update_progress(
        state,
        WorkflowStep.REGISTERING_FILES,
        5,
        "Registering source files...",
    )

    try:
        supabase = get_supabase_client()

        # Get report to find source file IDs
        report = supabase.table("reports").select("source_files").eq(
            "id", report_id
        ).single().execute()

        if not report.data or not report.data.get("source_files"):
            return mark_failed(state, "No source files found for report")

        # Extract file IDs
        source_files = report.data["source_files"]
        file_ids = [f["id"] if isinstance(f, dict) else f for f in source_files]

        logger.info(f"[WORKFLOW] Report {report_id} | REGISTER_FILES | Found {len(file_ids)} source files")

        # Fetch file metadata from database
        file_registry: list[FileRegistryEntry] = []

        for file_id in file_ids:
            file_record = supabase.table("source_files").select(
                "id, file_name, file_type, file_size, storage_path"
            ).eq("id", file_id).single().execute()

            if not file_record.data:
                logger.warning(f"[WORKFLOW] Report {report_id} | REGISTER_FILES | File not found: {file_id}")
                continue

            data = file_record.data
            file_ext = Path(data["file_name"]).suffix.lower()

            entry = FileRegistryEntry(
                file_id=data["id"],
                file_name=data["file_name"],
                file_type=file_ext,
                file_size=data.get("file_size", 0),
                storage_path=data.get("storage_path", ""),
                mime_type="",  # mime_type column doesn't exist in DB
            )
            file_registry.append(entry)

            logger.info(
                f"[WORKFLOW] Report {report_id} | REGISTER_FILES | "
                f"Registered: {entry.file_name} ({entry.file_type}, "
                f"{entry.file_size / 1024:.1f} KB)"
            )

        if not file_registry:
            return mark_failed(state, "No valid source files found")

        # Collect file types for skill selection
        input_file_types = {entry.file_type for entry in file_registry}

        # Update database progress
        supabase.table("reports").update({
            "status": "processing",
            "progress": 10,
        }).eq("id", report_id).execute()

        state = {
            **state,
            "file_registry": file_registry,
            "input_file_types": input_file_types,
        }

        logger.info(
            f"[WORKFLOW] Report {report_id} | REGISTER_FILES | "
            f"Registered {len(file_registry)} files, types: {input_file_types}"
        )

        state = mark_step_complete(state, WorkflowStep.REGISTERING_FILES, started_at)
        return update_progress(state, WorkflowStep.REGISTERING_FILES, 10, "Files registered")

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | REGISTER_FILES | Error: {e}")
        return mark_failed(state, f"File registration failed: {str(e)}")
