"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ============================================
# Auth Schemas
# ============================================


class SignupRequest(BaseModel):
    """User signup request."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User information response."""

    id: str
    email: str
    full_name: str | None = None


class AuthResponse(BaseModel):
    """Authentication response with tokens."""

    user: UserResponse
    access_token: str | None = None
    refresh_token: str | None = None


# ============================================
# File Schemas
# ============================================


class FileUploadResponse(BaseModel):
    """File upload response."""

    file_id: str
    file_name: str
    file_type: str
    file_size: int
    storage_path: str


class DriveFile(BaseModel):
    """Google Drive file information."""

    id: str
    name: str
    mime_type: str = Field(alias="mimeType")
    size: int | None = None

    class Config:
        populate_by_name = True


class DriveFileListResponse(BaseModel):
    """Google Drive file list response."""

    files: list[DriveFile]


class DriveSelectRequest(BaseModel):
    """Request to select files from Google Drive."""

    file_ids: list[str] = Field(min_length=1, max_length=20)


class DriveSelectedFile(BaseModel):
    """Selected file from Google Drive."""

    file_id: str
    file_name: str
    status: str


class DriveSelectResponse(BaseModel):
    """Response after selecting Drive files."""

    files: list[DriveSelectedFile]


class SourceFileResponse(BaseModel):
    """Source file information for listing."""

    id: str
    file_name: str
    file_type: str
    file_size: int | None = None
    source: str
    storage_path: str | None = None
    parsing_status: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Paginated list of user files."""

    files: list[SourceFileResponse]
    total: int
    page: int
    pages: int


# ============================================
# Report Schemas
# ============================================


class SlideCountConfig(BaseModel):
    """Slide count configuration for presentations."""

    min: int = Field(default=10, ge=5, le=30)
    max: int = Field(default=15, ge=5, le=30)


class GenerateReportRequest(BaseModel):
    """Request to generate a report."""

    title: str | None = Field(default=None, max_length=500)
    custom_instructions: str | None = Field(default=None, max_length=5000)
    detail_level: Literal["executive", "standard", "comprehensive"] = "standard"
    output_formats: list[Literal["pdf", "docx", "pptx"]] = Field(
        default=["pdf"],
        min_length=1,
    )
    slide_count: SlideCountConfig | None = None
    source_file_ids: list[str] = Field(min_length=1, max_length=20)


class GenerateReportResponse(BaseModel):
    """Response after starting report generation."""

    report_id: str
    status: str
    estimated_time_seconds: int


class OutputFile(BaseModel):
    """Generated output file information."""

    format: str
    storage_path: str | None = None
    download_url: str | None = None
    expires_at: datetime | None = None


class ReportMetrics(BaseModel):
    """Report generation metrics."""

    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    generation_time_seconds: int | None = None


class ReportResponse(BaseModel):
    """Full report information."""

    id: str
    title: str | None = None
    status: str
    progress: int = 0
    detail_level: str
    output_formats: list[str]
    custom_instructions: str | None = None
    source_files: list[dict] | None = None
    output_files: list[OutputFile] | None = None
    error_message: str | None = None
    generated_content: dict | None = None
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    generation_time_seconds: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class ReportStatusResponse(BaseModel):
    """Report generation status for polling."""

    status: str
    progress: int
    current_step: str
    error_message: str | None = None


class ReportListResponse(BaseModel):
    """Paginated list of reports."""

    reports: list[ReportResponse]
    total: int
    page: int
    pages: int


# ============================================
# LLM Generated Content Schemas
# ============================================


class ReportSection(BaseModel):
    """A section of the generated report."""

    title: str
    content: str
    subsections: list["ReportSection"] = []


class GeneratedReport(BaseModel):
    """LLM-generated report structure."""

    title: str
    executive_summary: str
    sections: list[ReportSection]
    key_findings: list[str]
    recommendations: list[str]
    sources: list[str]


class PresentationSlide(BaseModel):
    """A slide in the generated presentation."""

    type: Literal[
        "title", "section", "content", "key_findings",
        "stat_callout", "comparison", "timeline", "chart",
        "recommendations", "closing",
    ]
    title: str
    subtitle: str | None = None
    bullets: list[str] | None = None
    findings: list[str] | None = None
    items: list[str] | None = None
    # stat_callout
    stat_value: str | None = None
    stat_context: str | None = None
    # comparison
    left_items: list[str] | None = None
    right_items: list[str] | None = None
    left_label: str | None = None
    right_label: str | None = None
    # timeline
    events: list[dict[str, str]] | None = None
    # chart
    chart_type: str | None = None
    chart_title: str | None = None
    data_labels: list[str] | None = None
    data_values: list[float] | None = None
    contact: str | None = None
    notes: str | None = None


class GeneratedPresentation(BaseModel):
    """LLM-generated presentation structure."""

    title: str
    slides: list[PresentationSlide]


# ============================================
# Section Editing Schemas
# ============================================


class EditSectionRequest(BaseModel):
    """Request to edit a specific section of a report."""

    instructions: str = Field(min_length=1, max_length=5000)


class EditSectionResponse(BaseModel):
    """Response after editing a section."""

    section_path: str
    old_content: str
    new_content: str
    applied_at: datetime
