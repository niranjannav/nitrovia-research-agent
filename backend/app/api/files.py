"""File upload and Google Drive integration routes."""

import logging
import math
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser
from app.config import get_settings
from app.models.schemas import (
    DriveFileListResponse,
    DriveSelectRequest,
    DriveSelectResponse,
    FileListResponse,
    FileUploadResponse,
    SourceFileResponse,
)
from app.services.google_drive import GoogleDriveService
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    if "." in filename:
        return "." + filename.rsplit(".", 1)[1].lower()
    return ""


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    current_user: CurrentUser,
    file: Annotated[UploadFile, File(description="File to upload")],
):
    """Upload a file for report generation.

    If a file with the same name and size already exists for this user,
    returns the existing file instead of creating a duplicate.
    """
    # Validate file extension
    extension = get_file_extension(file.filename or "")
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate file size
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
        )

    supabase = get_supabase_client()

    # Check for existing duplicate (same filename + file size for this user)
    existing = supabase.table("source_files").select("*").eq(
        "user_id", current_user.id
    ).eq(
        "file_name", file.filename
    ).eq(
        "file_size", len(content)
    ).execute()

    if existing.data:
        # Return existing file instead of creating duplicate
        existing_file = existing.data[0]
        logger.info(f"[FILES] User {current_user.id} | Returning existing file: {existing_file['id']} ({file.filename})")
        return FileUploadResponse(
            file_id=existing_file["id"],
            file_name=existing_file["file_name"],
            file_type=existing_file["file_type"],
            file_size=existing_file["file_size"],
            storage_path=existing_file["storage_path"],
        )

    # Generate unique storage path for new file
    file_id = str(uuid.uuid4())
    storage_path = f"{current_user.id}/{file_id}{extension}"

    try:
        # Upload to Supabase Storage
        supabase.storage.from_(settings.upload_bucket).upload(
            storage_path,
            content,
            {"content-type": file.content_type or "application/octet-stream"},
        )

        # Create source_files record
        file_record = supabase.table("source_files").insert({
            "id": file_id,
            "user_id": current_user.id,
            "file_name": file.filename,
            "file_type": extension.lstrip("."),
            "file_size": len(content),
            "source": "upload",
            "storage_path": storage_path,
            "parsing_status": "pending",
        }).execute()

        logger.info(f"[FILES] User {current_user.id} | Uploaded new file: {file_id} ({file.filename})")

        return FileUploadResponse(
            file_id=file_id,
            file_name=file.filename,
            file_type=extension.lstrip("."),
            file_size=len(content),
            storage_path=storage_path,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )


@router.get("/list", response_model=FileListResponse)
async def list_user_files(
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
):
    """
    List all files uploaded by the current user.

    Files can be reused across multiple reports.
    """
    supabase = get_supabase_client()

    try:
        # Count total files for the user
        count_result = supabase.table("source_files").select(
            "id", count="exact"
        ).eq("user_id", current_user.id).execute()

        total = count_result.count or 0

        # Get paginated files
        offset = (page - 1) * limit
        files_result = supabase.table("source_files").select(
            "id, file_name, file_type, file_size, source, storage_path, parsing_status, created_at"
        ).eq(
            "user_id", current_user.id
        ).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        files = [SourceFileResponse(**f) for f in files_result.data]

        logger.info(f"[FILES] User {current_user.id} | Listed {len(files)} files (page {page})")

        return FileListResponse(
            files=files,
            total=total,
            page=page,
            pages=math.ceil(total / limit) if total > 0 else 1,
        )

    except Exception as e:
        logger.error(f"[FILES] User {current_user.id} | Failed to list files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}",
        )


@router.get("/drive/list", response_model=DriveFileListResponse)
async def list_drive_files(
    current_user: CurrentUser,
    folder_id: Annotated[str | None, Query(description="Google Drive folder ID")] = None,
):
    """List files from Google Drive."""
    if not settings.google_service_account_json:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google Drive integration not configured",
        )

    try:
        drive_service = GoogleDriveService(settings.google_service_account_json)
        files = await drive_service.list_files(folder_id)

        return DriveFileListResponse(files=files)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list Drive files: {str(e)}",
        )


@router.post("/drive/select", response_model=DriveSelectResponse)
async def select_drive_files(
    current_user: CurrentUser,
    request: DriveSelectRequest,
):
    """Select files from Google Drive for report generation."""
    if not settings.google_service_account_json:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google Drive integration not configured",
        )

    if len(request.file_ids) > settings.max_files_per_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum: {settings.max_files_per_report}",
        )

    drive_service = GoogleDriveService(settings.google_service_account_json)
    supabase = get_supabase_client()

    selected_files = []

    for drive_file_id in request.file_ids:
        try:
            # Download file from Google Drive
            content, filename, mime_type = await drive_service.download_file(drive_file_id)

            # Determine file extension
            extension = get_file_extension(filename)
            if extension not in ALLOWED_EXTENSIONS:
                continue  # Skip unsupported files

            # Check file size
            if len(content) > settings.max_file_size_bytes:
                continue  # Skip files that are too large

            # Check for existing duplicate (same filename + file size for this user)
            existing = supabase.table("source_files").select("*").eq(
                "user_id", current_user.id
            ).eq(
                "file_name", filename
            ).eq(
                "file_size", len(content)
            ).execute()

            if existing.data:
                # Return existing file instead of creating duplicate
                existing_file = existing.data[0]
                logger.info(f"[FILES] User {current_user.id} | Returning existing file from Drive: {existing_file['id']} ({filename})")
                selected_files.append({
                    "file_id": existing_file["id"],
                    "file_name": filename,
                    "status": "existing",
                })
                continue

            # Generate unique storage path for new file
            file_id = str(uuid.uuid4())
            storage_path = f"{current_user.id}/{file_id}{extension}"

            # Upload to Supabase Storage
            supabase.storage.from_(settings.upload_bucket).upload(
                storage_path,
                content,
                {"content-type": mime_type},
            )

            # Create source_files record
            supabase.table("source_files").insert({
                "id": file_id,
                "user_id": current_user.id,
                "file_name": filename,
                "file_type": extension.lstrip("."),
                "file_size": len(content),
                "source": "google_drive",
                "storage_path": storage_path,
                "google_drive_id": drive_file_id,
                "parsing_status": "pending",
            }).execute()

            logger.info(f"[FILES] User {current_user.id} | Imported new file from Drive: {file_id} ({filename})")

            selected_files.append({
                "file_id": file_id,
                "file_name": filename,
                "status": "queued",
            })

        except Exception as e:
            selected_files.append({
                "file_id": drive_file_id,
                "file_name": "Unknown",
                "status": f"failed: {str(e)}",
            })

    return DriveSelectResponse(files=selected_files)
