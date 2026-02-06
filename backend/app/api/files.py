"""File upload and Google Drive integration routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser
from app.config import get_settings
from app.models.schemas import (
    DriveFileListResponse,
    DriveSelectRequest,
    DriveSelectResponse,
    FileUploadResponse,
)
from app.services.google_drive import GoogleDriveService
from app.services.supabase import get_supabase_client

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
    """Upload a file for report generation."""
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

    # Generate unique storage path
    file_id = str(uuid.uuid4())
    storage_path = f"{current_user.id}/{file_id}{extension}"

    supabase = get_supabase_client()

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

            # Generate unique storage path
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
