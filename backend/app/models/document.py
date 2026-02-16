"""Document models for parsed content with metadata.

Defines structured document representations that carry metadata through
the parsing, embedding, and retrieval pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class DocumentMetadata:
    """Metadata attached to every document chunk.

    Ensures each chunk carries enough context for filtering and attribution
    during similarity search.
    """

    file_type: str  # e.g., "pdf", "docx", "xlsx", "pptx"
    file_name: str  # Original filename
    description: str  # Auto-generated description from file content
    user_id: str  # Owner identifier for filtering during similarity search
    source_file_id: Optional[str] = None  # Reference to source_files table
    chunk_index: int = 0  # Position of this chunk within the source file
    total_chunks: int = 1  # Total number of chunks from this source file
    page_number: Optional[int] = None  # Page/slide/sheet number if applicable
    sheet_name: Optional[str] = None  # Sheet name for Excel (XLSX) files
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to a JSON-serializable dict."""
        result = {
            "file_type": self.file_type,
            "file_name": self.file_name,
            "description": self.description,
            "user_id": self.user_id,
            "source_file_id": self.source_file_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
        }
        if self.page_number is not None:
            result["page_number"] = self.page_number
        if self.sheet_name is not None:
            result["sheet_name"] = self.sheet_name
        if self.extra:
            result["extra"] = self.extra
        return result


@dataclass
class DocumentChunk:
    """A single chunk of parsed content with its metadata.

    Represents the unit that gets embedded and stored in pgvector.
    """

    content: str
    metadata: DocumentMetadata

    def to_dict(self) -> dict[str, Any]:
        """Convert chunk to a JSON-serializable dict."""
        return {
            "content": self.content,
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class ParsedDocument:
    """A fully parsed document consisting of one or more chunks.

    Produced by file-type-specific parsers. Each chunk is ready to be
    embedded and stored in pgvector.
    """

    file_name: str
    file_type: str
    chunks: list[DocumentChunk]
    raw_text: str  # Full concatenated text for backward compatibility
    description: str = ""  # Auto-generated description
    created_at: Optional[datetime] = None

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "description": self.description,
            "total_chunks": self.total_chunks,
            "chunks": [c.to_dict() for c in self.chunks],
        }


def generate_description(content: str, max_length: int = 300) -> str:
    """Generate a description from the beginning of the file content.

    Uses a simple heuristic: takes the first meaningful lines of content,
    cleans them up, and truncates to max_length. This avoids any LLM cost.

    Args:
        content: The full text content of the document
        max_length: Maximum character length for the description

    Returns:
        A brief description string
    """
    if not content or not content.strip():
        return "Empty document"

    # Take the first portion of text
    lines = content.strip().split("\n")
    meaningful_lines = []
    chars = 0

    for line in lines:
        stripped = line.strip()
        # Skip structural markers like [Page 1], [Sheet: ...], [Slide 1]
        if stripped and not stripped.startswith("[") and not stripped.startswith("==="):
            meaningful_lines.append(stripped)
            chars += len(stripped)
            if chars >= max_length:
                break

    if not meaningful_lines:
        # Fallback: use first non-empty content
        text = content.strip()[:max_length]
        return text.rstrip() + ("..." if len(content.strip()) > max_length else "")

    description = " ".join(meaningful_lines)
    if len(description) > max_length:
        description = description[:max_length].rstrip() + "..."

    return description
