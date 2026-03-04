"""Analytics API routes.

Provides endpoints for:
  - Schema inference (scan Excel structure, get mapping from Claude)
  - Mapping management (save, confirm, update)
  - Excel upload and data ingestion
  - Analytics report generation
  - Upload history
"""

import logging
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import CurrentUser
from app.services.analytics_data_service import AnalyticsDataService
from app.services.schema_inference_service import SchemaInferenceService, SchemaMapping
from app.services.sheet_scanner import SheetScanner
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
ALLOWED_EXCEL_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",  # some clients send this
}
MAX_EXCEL_SIZE_MB = 50
VALID_DOMAINS = {"sales", "production", "qa", "finance"}


# ── Request / Response schemas ───────────────────────────────────────────────

class SchemaMappingResponse(BaseModel):
    mapping_id: str | None = None
    mapping: dict
    confirmed: bool = False
    message: str = ""


class ConfirmMappingRequest(BaseModel):
    mapping_id: str
    mapping: dict | None = None   # optional: user-edited mapping to persist


class AnalyticsUploadResponse(BaseModel):
    upload_id: str
    domain: str
    file_name: str
    period_start: date
    period_end: date
    row_count: int
    status: str
    mapping_id: str | None = None


class GenerateAnalyticsReportRequest(BaseModel):
    domain: str
    report_period: str = "monthly"    # weekly | monthly | quarterly | annual
    as_of_date: date | None = None
    output_formats: list[str] = Field(default=["pdf"])
    custom_instructions: str | None = None
    primary_metric: str = "revenue"   # revenue | quantity_litres


class GenerateAnalyticsReportResponse(BaseModel):
    report_id: str
    status: str
    domain: str
    estimated_seconds: int = 60


# ── Schema inference endpoints ───────────────────────────────────────────────

@router.post("/schema/infer", response_model=SchemaMappingResponse)
@limiter.limit("5/minute")
async def infer_schema(
    request: Request,
    current_user: CurrentUser,
    domain: str = Query(..., description="Analytics domain: sales | production | qa | finance"),
    file: Annotated[UploadFile, File(description="Excel file to analyse")] = ...,
):
    """Scan an Excel file and use Claude to infer a SchemaMapping.

    The mapping describes which sheets contain transactional data, which
    columns map to standard analytics fields, and how time periods are encoded.

    This is called once per new file format. The resulting mapping should be
    reviewed by the user and then confirmed via POST /analytics/schema/confirm.
    """
    _validate_domain(domain)
    file_content = await _read_and_validate_excel(file)

    scanner = SheetScanner()
    inference_service = SchemaInferenceService()

    try:
        sheet_summary = scanner.scan(file_content, file.filename or "upload.xlsx")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        mapping = await inference_service.infer(sheet_summary, domain)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Save as unconfirmed draft
    mapping_id = inference_service.save_mapping(
        user_id=current_user.id,
        domain=domain,
        mapping=mapping,
        confirmed=False,
    )

    return SchemaMappingResponse(
        mapping_id=mapping_id,
        mapping=mapping.model_dump(mode="json"),
        confirmed=False,
        message=(
            f"Schema inferred with {mapping.confidence:.0%} confidence. "
            "Review and confirm before uploading data."
        ),
    )


@router.get("/schema/{domain}", response_model=SchemaMappingResponse)
async def get_schema(
    domain: str,
    current_user: CurrentUser,
):
    """Get the saved (confirmed) schema mapping for a domain."""
    _validate_domain(domain)
    service = SchemaInferenceService()
    mapping = service.get_mapping(current_user.id, domain)

    if not mapping:
        raise HTTPException(
            status_code=404,
            detail=f"No confirmed schema mapping found for domain '{domain}'. "
                   "Upload an Excel file and infer the schema first.",
        )

    return SchemaMappingResponse(
        mapping=mapping.model_dump(mode="json"),
        confirmed=True,
    )


@router.post("/schema/confirm")
async def confirm_schema(
    body: ConfirmMappingRequest,
    current_user: CurrentUser,
):
    """Confirm a schema mapping (optionally with user edits).

    After confirmation, the mapping is used for all future Excel uploads
    of this domain.
    """
    service = SchemaInferenceService()

    if body.mapping:
        # User has edited the mapping — validate and save updated version
        try:
            updated = SchemaMapping.model_validate(body.mapping)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid mapping: {e}")
        service.update_mapping(body.mapping_id, current_user.id, updated)

    service.confirm_mapping(body.mapping_id, current_user.id)
    return {"status": "confirmed", "mapping_id": body.mapping_id}


# ── Upload endpoints ─────────────────────────────────────────────────────────

@router.post("/upload", response_model=AnalyticsUploadResponse)
@limiter.limit("5/minute")
async def upload_analytics_excel(
    request: Request,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    domain: str = Query(...),
    period_start: date = Query(..., description="Start date of data in this file (YYYY-MM-DD)"),
    period_end: date = Query(..., description="End date of data in this file (YYYY-MM-DD)"),
    file: Annotated[UploadFile, File(description="Excel file containing analytics data")] = ...,
):
    """Upload an Excel file and ingest its data into the analytics store.

    Schema inference is automatic — no prior schema confirmation is needed.
    If a confirmed mapping already exists for the domain it is reused;
    otherwise Claude infers one silently during ingestion.

    Data is ingested in the background. Poll the returned upload_id via
    GET /analytics/uploads to check status.
    """
    _validate_domain(domain)

    if period_start > period_end:
        raise HTTPException(status_code=400, detail="period_start must be before period_end")

    file_content = await _read_and_validate_excel(file)
    file_name = file.filename or f"{domain}_upload.xlsx"

    # Try to reuse existing confirmed mapping
    inference_service = SchemaInferenceService()
    existing_mapping = inference_service.get_mapping(current_user.id, domain)

    # Find mapping_id if one already exists
    existing_mapping_id: str | None = None
    if existing_mapping:
        supabase_client = get_supabase_client()
        mapping_row = (
            supabase_client.table("analytics_schema_mappings")
            .select("id")
            .eq("user_id", current_user.id)
            .eq("domain", domain)
            .eq("confirmed_by_user", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        existing_mapping_id = mapping_row.data[0]["id"] if mapping_row.data else None

    # Store file in Supabase Storage
    supabase = get_supabase_client()
    storage_path = f"analytics/{current_user.id}/{domain}/{uuid.uuid4().hex[:8]}_{file_name}"
    try:
        supabase.storage.from_("uploads").upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        )
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(status_code=500, detail="File storage failed")

    # Create upload record (mapping_id may be None if we need to auto-infer)
    data_service = AnalyticsDataService()
    upload_id = data_service.create_upload_record(
        user_id=current_user.id,
        domain=domain,
        mapping_id=existing_mapping_id,
        period_start=period_start,
        period_end=period_end,
        file_name=file_name,
        storage_path=storage_path,
    )

    # Kick off background ingestion (auto-infers schema if needed)
    background_tasks.add_task(
        _ingest_background,
        upload_id=upload_id,
        user_id=current_user.id,
        domain=domain,
        file_content=file_content,
        existing_mapping=existing_mapping,
    )

    return AnalyticsUploadResponse(
        upload_id=upload_id,
        domain=domain,
        file_name=file_name,
        period_start=period_start,
        period_end=period_end,
        row_count=0,          # updated when background task completes
        status="processing",
        mapping_id=existing_mapping_id,
    )


@router.get("/uploads")
async def list_uploads(
    current_user: CurrentUser,
    domain: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    """List analytics data uploads for the current user."""
    service = AnalyticsDataService()
    uploads = service.list_uploads(current_user.id, domain=domain, limit=limit)
    return {"uploads": uploads, "total": len(uploads)}


@router.get("/uploads/{upload_id}")
async def get_upload_status(
    upload_id: str,
    current_user: CurrentUser,
):
    """Get the status and details of a specific upload."""
    supabase = get_supabase_client()
    result = (
        supabase.table("analytics_uploads")
        .select("*")
        .eq("id", upload_id)
        .eq("user_id", current_user.id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Upload not found")
    return result.data


@router.delete("/uploads/{upload_id}", status_code=204)
async def delete_upload(
    upload_id: str,
    current_user: CurrentUser,
):
    """Delete an upload and all its associated records."""
    supabase = get_supabase_client()

    # Verify ownership
    row = (
        supabase.table("analytics_uploads")
        .select("id, storage_path")
        .eq("id", upload_id)
        .eq("user_id", current_user.id)
        .single()
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=404, detail="Upload not found")

    storage_path = row.data.get("storage_path")

    # Delete records (cascades via FK in migration) and the upload row
    supabase.table("analytics_uploads").delete().eq("id", upload_id).execute()

    # Remove file from storage
    if storage_path:
        try:
            supabase.storage.from_("uploads").remove([storage_path])
        except Exception as e:
            logger.warning(f"Failed to delete storage file {storage_path}: {e}")


# ── Report generation endpoint ───────────────────────────────────────────────

@router.post("/reports/generate", response_model=GenerateAnalyticsReportResponse)
@limiter.limit("2/minute")
async def generate_analytics_report(
    request: Request,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    body: GenerateAnalyticsReportRequest,
):
    """Generate an analytics report for a domain.

    Queries accumulated data, calculates all time-based metrics, generates
    charts, and uses Claude to write a narrative with recommendations.
    Returns a report_id; poll GET /reports/{report_id}/status for progress.
    """
    _validate_domain(body.domain)

    as_of = body.as_of_date or date.today()

    # Create report record using existing reports table
    supabase = get_supabase_client()
    report_row = (
        supabase.table("reports")
        .insert({
            "user_id": current_user.id,
            "title": f"{body.domain.capitalize()} Analytics Report — {as_of.strftime('%B %Y')}",
            "status": "pending",
            "progress": 0,
            "current_step": "Initialising analytics report",
            "output_formats": body.output_formats,
            "custom_instructions": body.custom_instructions or "",
            "detail_level": "comprehensive",
            "source_files": [],
        })
        .execute()
    )

    if not report_row.data:
        raise HTTPException(status_code=500, detail="Failed to create report record")

    report_id = report_row.data[0]["id"]

    background_tasks.add_task(
        _run_analytics_report,
        report_id=report_id,
        user_id=current_user.id,
        domain=body.domain,
        as_of=as_of,
        report_period=body.report_period,
        output_formats=body.output_formats,
        primary_metric=body.primary_metric,
        custom_instructions=body.custom_instructions,
    )

    return GenerateAnalyticsReportResponse(
        report_id=report_id,
        status="pending",
        domain=body.domain,
        estimated_seconds=60,
    )


# ── Background tasks ─────────────────────────────────────────────────────────

async def _ingest_background(
    upload_id: str,
    user_id: str,
    domain: str,
    file_content: bytes,
    existing_mapping: SchemaMapping | None,
) -> None:
    """Background task: auto-infer schema if needed, extract records, store in DB."""
    from app.services.generic_data_extractor import GenericDataExtractor
    from app.services.sheet_scanner import SheetScanner

    data_service = AnalyticsDataService()
    inference_service = SchemaInferenceService()

    try:
        mapping = existing_mapping

        if mapping is None:
            # Auto-infer schema silently (no user review step)
            logger.info(f"Auto-inferring schema for upload_id={upload_id}, domain={domain}")
            scanner = SheetScanner()
            file_name = f"{domain}_upload.xlsx"
            sheet_summary = scanner.scan(file_content, file_name)
            mapping = await inference_service.infer(sheet_summary, domain)
            mapping_id = inference_service.auto_confirm(mapping, user_id, domain)
            data_service.set_upload_mapping(upload_id, mapping_id)
            logger.info(f"Schema auto-confirmed: mapping_id={mapping_id}")

        extractor = GenericDataExtractor()
        records = extractor.extract(file_content, mapping)

        if domain == "finance":
            row_count = data_service.ingest_finance(upload_id, user_id, records)
        else:
            row_count = data_service.ingest(upload_id, user_id, domain, records)

        data_service.mark_upload_complete(upload_id, row_count)
        logger.info(f"Background ingestion complete: upload_id={upload_id}, rows={row_count}")
    except Exception as e:
        logger.error(f"Background ingestion failed: upload_id={upload_id}, error={e}")
        data_service.mark_upload_failed(upload_id, str(e))


async def _run_analytics_report(
    report_id: str,
    user_id: str,
    domain: str,
    as_of: date,
    report_period: str,
    output_formats: list[str],
    primary_metric: str,
    custom_instructions: str | None,
) -> None:
    """Background task: run analytics workflow and generate report."""
    from app.workflows.analytics_report_workflow import run_analytics_workflow

    try:
        await run_analytics_workflow(
            report_id=report_id,
            user_id=user_id,
            domain=domain,
            as_of=as_of,
            report_period=report_period,
            output_formats=output_formats,
            primary_metric=primary_metric,
            custom_instructions=custom_instructions,
        )
    except Exception as e:
        logger.error(f"Analytics workflow failed: report_id={report_id}, error={e}")
        supabase = get_supabase_client()
        supabase.table("reports").update({
            "status": "failed",
            "error_message": str(e)[:500],
        }).eq("id", report_id).execute()


# ── Analytics chat endpoint ───────────────────────────────────────────────────

class _ChatMessage(BaseModel):
    role: str   # 'user' | 'assistant'
    content: str


class AnalyticsChatRequest(BaseModel):
    domain: str
    message: str
    conversation_history: list[_ChatMessage] = Field(default_factory=list)


class AnalyticsChatResponse(BaseModel):
    answer: str


@router.post("/chat", response_model=AnalyticsChatResponse)
@limiter.limit("10/minute")
async def analytics_chat(
    request: Request,
    current_user: CurrentUser,
    body: AnalyticsChatRequest,
):
    """Ad-hoc conversational Q&A about the user's analytics data."""
    _validate_domain(body.domain)

    from app.llm.gateway import create_gateway_from_settings
    from app.llm.config import TaskType
    from datetime import date as _date
    import json

    data_service = AnalyticsDataService()
    as_of = _date.today()

    try:
        if body.domain == "finance":
            records = data_service.query_all_finance_for_metrics(current_user.id)
            context_json = json.dumps(
                {"domain": "finance", "record_count": len(records),
                 "as_of": as_of.isoformat(),
                 "recent_records": records[-12:] if records else []},
                default=str,
            )[:8000]
        else:
            records = data_service.query_all_for_metrics(
                user_id=current_user.id,
                domain=body.domain,
                as_of=as_of,
                lookback_years=2,
            )
            if body.domain == "sales":
                from app.services.metrics_calculator import compute_sales_metrics
                try:
                    metrics = compute_sales_metrics(records, as_of, "revenue")
                    context_json = json.dumps(metrics.to_dict(), default=str)[:8000]
                except Exception:
                    context_json = json.dumps(
                        {"domain": body.domain, "record_count": len(records)},
                        default=str,
                    )
            else:
                context_json = json.dumps(
                    {"domain": body.domain, "record_count": len(records)},
                    default=str,
                )
    except Exception as e:
        logger.warning(f"Could not compute metrics for chat context: {e}")
        context_json = json.dumps({"domain": body.domain, "error": "no data available"})

    system_prompt = (
        f"You are an analytics assistant for a dairy company. "
        f"The user is asking about their {body.domain} data. "
        f"Here is the current data context (JSON):\n{context_json}\n\n"
        "Answer questions directly using the data. Keep responses concise and precise. "
        "If data is unavailable for a question, say so clearly."
    )

    messages = [
        {"role": m.role, "content": m.content}
        for m in body.conversation_history
    ]
    messages.append({"role": "user", "content": body.message})

    gateway = create_gateway_from_settings()
    try:
        response_text, _ = await gateway.generate_text(
            task=TaskType.CLASSIFICATION,
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000,
        )
    except Exception as e:
        logger.error(f"Chat LLM call failed: {e}")
        raise HTTPException(status_code=500, detail="Chat generation failed")

    return AnalyticsChatResponse(answer=response_text)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_domain(domain: str) -> None:
    if domain not in VALID_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain '{domain}'. Valid options: {sorted(VALID_DOMAINS)}",
        )


async def _read_and_validate_excel(file: UploadFile) -> bytes:
    """Read and validate an uploaded Excel file."""
    filename = file.filename or ""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext not in ALLOWED_EXCEL_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only Excel files are accepted (.xlsx, .xls). Got: '{ext}'",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_EXCEL_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_EXCEL_SIZE_MB} MB.",
        )

    if len(content) < 4:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupt")

    return content
