"""Google Drive API integration service."""

import base64
import io
import json
import logging
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

# MIME types we can process
SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    # Google Docs formats that can be exported
    "application/vnd.google-apps.document": ".docx",
    "application/vnd.google-apps.spreadsheet": ".xlsx",
    "application/vnd.google-apps.presentation": ".pptx",
}

# Export MIME types for Google Docs formats
EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class GoogleDriveService:
    """Service for interacting with Google Drive API."""

    def __init__(self, service_account_json_b64: str):
        """
        Initialize Google Drive service with service account credentials.

        Args:
            service_account_json_b64: Base64 encoded service account JSON
        """
        # Decode base64 credentials
        credentials_json = base64.b64decode(service_account_json_b64).decode("utf-8")
        credentials_dict = json.loads(credentials_json)

        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )

        # Build Drive service
        self.service = build("drive", "v3", credentials=credentials)

    async def list_files(
        self,
        folder_id: str | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List files in a folder or root.

        Args:
            folder_id: Optional folder ID to list files from
            page_size: Number of files to return

        Returns:
            List of file metadata dicts
        """
        try:
            # Build query
            query_parts = []

            # Filter by supported MIME types
            mime_conditions = [f"mimeType='{mime}'" for mime in SUPPORTED_MIME_TYPES.keys()]
            mime_conditions.append("mimeType='application/vnd.google-apps.folder'")
            query_parts.append(f"({' or '.join(mime_conditions)})")

            # Filter by folder if specified
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")

            # Exclude trashed files
            query_parts.append("trashed=false")

            query = " and ".join(query_parts)

            # Execute query
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                fields="files(id, name, mimeType, size)",
            ).execute()

            files = results.get("files", [])

            return [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "mimeType": f["mimeType"],
                    "size": int(f.get("size", 0)) if f.get("size") else None,
                }
                for f in files
            ]

        except Exception as e:
            logger.error(f"Failed to list Drive files: {e}")
            raise

    async def download_file(self, file_id: str) -> tuple[bytes, str, str]:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            Tuple of (file_content, filename, mime_type)
        """
        try:
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="name, mimeType, size",
            ).execute()

            filename = file_metadata["name"]
            mime_type = file_metadata["mimeType"]

            # Check if it's a Google Docs format that needs export
            if mime_type in EXPORT_MIME_TYPES:
                # Export to Office format
                export_mime = EXPORT_MIME_TYPES[mime_type]
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType=export_mime,
                )

                # Update filename extension
                extension = SUPPORTED_MIME_TYPES.get(mime_type, "")
                if not filename.endswith(extension):
                    filename = filename + extension

                mime_type = export_mime

            else:
                # Download directly
                request = self.service.files().get_media(fileId=file_id)

            # Download content
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            content = buffer.getvalue()

            return content, filename, mime_type

        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            raise
