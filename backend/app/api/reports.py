"""Report generation routes."""

import asyncio
import logging
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.config import get_settings
from app.models.schemas import (
    EditSectionRequest,
    EditSectionResponse,
    GenerateReportRequest,
    GenerateReportResponse,
    ReportListResponse,
    ReportResponse,
    ReportStatusResponse,
)
from app.services.llm_service import LLMService
from app.services.report_generator import ReportGeneratorService
from app.services.supabase import get_supabase_client

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    current_user: CurrentUser,
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
):
    """Start report generation from uploaded files."""
    # Validate file count
    if len(request.source_file_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one source file is required",
        )

    if len(request.source_file_ids) > settings.max_files_per_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum: {settings.max_files_per_report}",
        )

    # Validate output formats
    valid_formats = {"pdf", "docx", "pptx"}
    if not all(fmt in valid_formats for fmt in request.output_formats):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid output format. Allowed: {', '.join(valid_formats)}",
        )

    supabase = get_supabase_client()

    # Verify all source files exist and belong to user
    for file_id in request.source_file_ids:
        file_check = supabase.table("source_files").select("id").eq(
            "id", file_id
        ).eq("user_id", current_user.id).execute()

        if not file_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source file not found: {file_id}",
            )

    # Create report record
    report_id = str(uuid4())

    report_data = {
        "id": report_id,
        "created_by": current_user.id,
        "title": request.title,
        "custom_instructions": request.custom_instructions,
        "detail_level": request.detail_level,
        "output_formats": request.output_formats,
        "slide_count_min": request.slide_count.min if request.slide_count else 10,
        "slide_count_max": request.slide_count.max if request.slide_count else 15,
        "status": "pending",
        "progress": 0,
        "source_files": [{"id": fid} for fid in request.source_file_ids],
    }

    supabase.table("reports").insert(report_data).execute()

    # Note: Files are NOT linked via report_id to allow reuse across reports.
    # The report's source_files JSON contains the file IDs.
    # Files can be used in multiple reports without modification.

    logger.info(f"[REPORT] Created report {report_id} with {len(request.source_file_ids)} source files")

    # Start background generation
    background_tasks.add_task(
        run_report_generation,
        report_id=report_id,
        user_id=current_user.id,
    )

    # Estimate time based on file count and detail level
    estimated_time = len(request.source_file_ids) * 30  # 30 seconds per file base
    if request.detail_level == "comprehensive":
        estimated_time *= 2
    elif request.detail_level == "executive":
        estimated_time = int(estimated_time * 0.7)

    return GenerateReportResponse(
        report_id=report_id,
        status="processing",
        estimated_time_seconds=estimated_time,
    )


async def run_report_generation(report_id: str, user_id: str):
    """Run report generation in background."""
    try:
        generator = ReportGeneratorService()
        await generator.generate(report_id, user_id)
    except Exception as e:
        logger.error(f"Report generation failed for {report_id}: {e}")
        # Update report status to failed
        supabase = get_supabase_client()
        supabase.table("reports").update({
            "status": "failed",
            "error_message": str(e),
        }).eq("id", report_id).execute()


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    current_user: CurrentUser,
    report_id: str,
):
    """Get report details."""
    supabase = get_supabase_client()

    report = supabase.table("reports").select("*").eq(
        "id", report_id
    ).eq("created_by", current_user.id).single().execute()

    if not report.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportResponse(**report.data)


@router.get("/{report_id}/status", response_model=ReportStatusResponse)
async def get_report_status(
    current_user: CurrentUser,
    report_id: str,
):
    """Get report generation status for polling."""
    supabase = get_supabase_client()

    report = supabase.table("reports").select(
        "status", "progress", "error_message"
    ).eq("id", report_id).eq("created_by", current_user.id).single().execute()

    if not report.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Get current step description
    current_step = get_step_description(report.data["status"], report.data["progress"])

    return ReportStatusResponse(
        status=report.data["status"],
        progress=report.data["progress"],
        current_step=current_step,
        error_message=report.data.get("error_message"),
    )


def get_step_description(status: str, progress: int) -> str:
    """Get human-readable step description."""
    if status == "pending":
        return "Waiting to start..."
    elif status == "processing":
        if progress < 10:
            return "Registering source files..."
        elif progress < 50:
            return "Research agent analyzing documents..."
        elif progress < 60:
            return "Generating report content..."
        elif progress < 80:
            return "Creating presentation slides..."
        elif progress < 95:
            return "Rendering output files..."
        else:
            return "Uploading files..."
    elif status == "completed":
        return "Report ready for download"
    elif status == "failed":
        return "Generation failed"
    return "Processing..."


@router.get("", response_model=ReportListResponse)
async def list_reports(
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
):
    """List user's reports with pagination."""
    supabase = get_supabase_client()

    # Build query
    query = supabase.table("reports").select("*", count="exact").eq(
        "created_by", current_user.id
    )

    if status_filter:
        query = query.eq("status", status_filter)

    # Order by created_at descending
    query = query.order("created_at", desc=True)

    # Pagination
    offset = (page - 1) * limit
    query = query.range(offset, offset + limit - 1)

    result = query.execute()

    total = result.count or 0
    pages = (total + limit - 1) // limit

    return ReportListResponse(
        reports=[ReportResponse(**r) for r in result.data],
        total=total,
        page=page,
        pages=pages,
    )


@router.delete("/{report_id}")
async def delete_report(
    current_user: CurrentUser,
    report_id: str,
):
    """Delete a report and its associated files."""
    supabase = get_supabase_client()

    # Verify report exists and belongs to user
    report = supabase.table("reports").select("*").eq(
        "id", report_id
    ).eq("created_by", current_user.id).single().execute()

    if not report.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Delete output files from storage (generated PDFs, DOCX, PPTX)
    output_files = report.data.get("output_files", [])
    for output_file in output_files:
        if storage_path := output_file.get("storage_path"):
            try:
                supabase.storage.from_(settings.output_bucket).remove([storage_path])
            except Exception:
                pass  # Ignore storage deletion errors

    # Note: Source files are NOT deleted to allow reuse across reports.
    # Users can manage source files separately via /files endpoints.

    # Delete report record
    supabase.table("reports").delete().eq("id", report_id).execute()

    logger.info(f"[REPORT] Deleted report {report_id}")

    return {"success": True}


@router.patch("/{report_id}/sections/{section_path:path}", response_model=EditSectionResponse)
async def edit_report_section(
    current_user: CurrentUser,
    report_id: str,
    section_path: str,
    request: EditSectionRequest,
):
    """
    Edit a specific section of a report using LLM.

    section_path examples:
    - "executive_summary" - edit executive summary
    - "sections.0" - edit first section
    - "sections.1.subsections.0" - edit first subsection of second section
    - "key_findings" - edit key findings list
    - "recommendations" - edit recommendations list
    """
    supabase = get_supabase_client()

    # Get report and verify ownership
    report = supabase.table("reports").select("*").eq(
        "id", report_id
    ).eq("created_by", current_user.id).single().execute()

    if not report.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.data.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit completed reports",
        )

    generated_content = report.data.get("generated_content")
    if not generated_content or not generated_content.get("report"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report has no generated content",
        )

    report_data = generated_content["report"]

    # Extract the section to edit
    section_title, old_content = _extract_section(report_data, section_path)

    if old_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found: {section_path}",
        )

    # Build context summary for LLM
    report_context = f"""Report Title: {report_data.get('title', 'Untitled')}

Executive Summary: {report_data.get('executive_summary', '')[:500]}...

Sections: {', '.join(s.get('title', '') for s in report_data.get('sections', []))}

Key Findings: {len(report_data.get('key_findings', []))} items"""

    # Call LLM to edit section
    logger.info(f"[EDIT] Report {report_id} | Editing section: {section_path}")

    llm_service = LLMService(settings.anthropic_api_key)
    new_content = llm_service.edit_section(
        section_title=section_title,
        section_content=old_content if isinstance(old_content, str) else str(old_content),
        user_instructions=request.instructions,
        report_context=report_context,
    )

    # Update the section in generated_content
    updated_report = _update_section(report_data, section_path, new_content)
    generated_content["report"] = updated_report

    # Save to database with last_edited timestamp
    supabase.table("reports").update({
        "generated_content": generated_content,
        "last_edited_at": datetime.now().isoformat(),
    }).eq("id", report_id).execute()

    logger.info(f"[EDIT] Report {report_id} | Section updated: {section_path}")

    return EditSectionResponse(
        section_path=section_path,
        old_content=old_content if isinstance(old_content, str) else str(old_content),
        new_content=new_content,
        applied_at=datetime.now(),
    )


def _extract_section(report_data: dict, section_path: str) -> tuple[str, str | list | None]:
    """
    Extract section content from report data.

    Returns tuple of (section_title, section_content).
    """
    parts = section_path.split(".")

    if parts[0] == "executive_summary":
        return "Executive Summary", report_data.get("executive_summary")

    if parts[0] == "key_findings":
        return "Key Findings", report_data.get("key_findings")

    if parts[0] == "recommendations":
        return "Recommendations", report_data.get("recommendations")

    if parts[0] == "sections":
        try:
            sections = report_data.get("sections", [])
            current = sections[int(parts[1])]
            title = current.get("title", f"Section {parts[1]}")

            # Drill down into subsections if needed
            for i in range(2, len(parts), 2):
                if parts[i] == "subsections":
                    current = current.get("subsections", [])[int(parts[i + 1])]
                    title = current.get("title", title)

            return title, current.get("content", "")
        except (IndexError, KeyError, ValueError):
            return "", None

    return "", None


def _update_section(report_data: dict, section_path: str, new_content: str) -> dict:
    """
    Update section content in report data.

    Returns the updated report data dict.
    """
    import copy
    updated = copy.deepcopy(report_data)
    parts = section_path.split(".")

    if parts[0] == "executive_summary":
        updated["executive_summary"] = new_content
        return updated

    if parts[0] in ("key_findings", "recommendations"):
        # Parse new_content as list if it looks like a list
        if new_content.strip().startswith("["):
            try:
                import json
                updated[parts[0]] = json.loads(new_content)
            except json.JSONDecodeError:
                # Try to parse as bullet points
                lines = [l.strip().lstrip("•-*").strip()
                        for l in new_content.strip().split("\n")
                        if l.strip()]
                updated[parts[0]] = lines
        else:
            lines = [l.strip().lstrip("•-*").strip()
                    for l in new_content.strip().split("\n")
                    if l.strip()]
            updated[parts[0]] = lines
        return updated

    if parts[0] == "sections":
        try:
            idx = int(parts[1])
            if len(parts) == 2:
                # Editing section content directly
                updated["sections"][idx]["content"] = new_content
            else:
                # Drill down into subsections
                current = updated["sections"][idx]
                for i in range(2, len(parts) - 2, 2):
                    if parts[i] == "subsections":
                        current = current["subsections"][int(parts[i + 1])]
                # Set the final content
                if parts[-2] == "subsections":
                    current["subsections"][int(parts[-1])]["content"] = new_content
                else:
                    current["content"] = new_content
        except (IndexError, KeyError, ValueError) as e:
            logger.warning(f"Failed to update section {section_path}: {e}")

    return updated
