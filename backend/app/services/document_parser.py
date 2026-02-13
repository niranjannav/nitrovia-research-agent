"""Document parsing service for multiple file formats.

Each parser extracts content in high-fidelity format and produces
ParsedDocument objects with per-chunk metadata, ready for embedding
and storage in pgvector.
"""

import logging
from abc import ABC, abstractmethod
from io import BytesIO

import fitz  # PyMuPDF
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

from app.models.document import (
    DocumentChunk,
    DocumentMetadata,
    ParsedDocument,
    generate_description,
)

logger = logging.getLogger(__name__)

# Maximum characters per chunk for embedding
MAX_CHUNK_CHARS = 4000


class BaseDocumentParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_content: bytes) -> str:
        """Extract text content from document.

        Args:
            file_content: Raw file bytes

        Returns:
            Extracted text content
        """
        pass

    @abstractmethod
    def parse_to_document(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        source_file_id: str | None = None,
    ) -> ParsedDocument:
        """Parse file into a structured ParsedDocument with metadata.

        Args:
            file_content: Raw file bytes
            file_name: Original filename
            user_id: Owner identifier for search filtering
            source_file_id: Optional reference to source_files table

        Returns:
            ParsedDocument with chunks and metadata
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        pass

    def _get_file_type(self) -> str:
        """Get the file type string for metadata."""
        exts = self.supported_extensions()
        return exts[0].lstrip(".") if exts else "unknown"

    def _create_metadata(
        self,
        file_name: str,
        user_id: str,
        description: str,
        source_file_id: str | None = None,
        chunk_index: int = 0,
        total_chunks: int = 1,
        page_number: int | None = None,
        sheet_name: str | None = None,
    ) -> DocumentMetadata:
        """Create metadata for a document chunk."""
        return DocumentMetadata(
            file_type=self._get_file_type(),
            file_name=file_name,
            description=description,
            user_id=user_id,
            source_file_id=source_file_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            page_number=page_number,
            sheet_name=sheet_name,
        )


class PDFParser(BaseDocumentParser):
    """Parser for PDF files using PyMuPDF."""

    def parse(self, file_content: bytes) -> str:
        """Extract text from PDF."""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            text_parts = []

            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"[Page {page_num}]\n{page_text}")

            doc.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    def parse_to_document(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        source_file_id: str | None = None,
    ) -> ParsedDocument:
        """Parse PDF into structured document with per-page chunks."""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            chunks: list[DocumentChunk] = []
            text_parts: list[str] = []

            page_count = len(doc)
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"[Page {page_num}]\n{page_text}")

            raw_text = "\n\n".join(text_parts)
            description = generate_description(raw_text)

            # Create chunks per page
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                if page_text.strip():
                    metadata = self._create_metadata(
                        file_name=file_name,
                        user_id=user_id,
                        description=description,
                        source_file_id=source_file_id,
                        chunk_index=len(chunks),
                        total_chunks=page_count,
                        page_number=page_num,
                    )
                    chunks.append(DocumentChunk(content=page_text.strip(), metadata=metadata))

            doc.close()

            # Update total_chunks in all metadata
            for chunk in chunks:
                chunk.metadata.total_chunks = len(chunks)

            return ParsedDocument(
                file_name=file_name,
                file_type="pdf",
                chunks=chunks,
                raw_text=raw_text,
                description=description,
            )

        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    def supported_extensions(self) -> list[str]:
        return [".pdf"]


class DOCXParser(BaseDocumentParser):
    """Parser for DOCX files using python-docx."""

    def parse(self, file_content: bytes) -> str:
        """Extract text from DOCX."""
        try:
            doc = Document(BytesIO(file_content))
            text_parts = []

            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            # Also extract text from tables
            for table in doc.tables:
                table_text = []
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        table_text.append(row_text)
                if table_text:
                    text_parts.append("\n[Table]\n" + "\n".join(table_text))

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            raise ValueError(f"Failed to parse DOCX: {str(e)}")

    def parse_to_document(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        source_file_id: str | None = None,
    ) -> ParsedDocument:
        """Parse DOCX into structured document with logical chunks."""
        try:
            doc = Document(BytesIO(file_content))
            chunks: list[DocumentChunk] = []
            raw_text = self.parse(file_content)
            description = generate_description(raw_text)

            # Build chunks from paragraphs, grouping by size
            current_chunk_text: list[str] = []
            current_chars = 0

            for para in doc.paragraphs:
                if para.text.strip():
                    # Start a new chunk if adding this paragraph would exceed limit
                    if current_chars + len(para.text) > MAX_CHUNK_CHARS and current_chunk_text:
                        content = "\n\n".join(current_chunk_text)
                        metadata = self._create_metadata(
                            file_name=file_name,
                            user_id=user_id,
                            description=description,
                            source_file_id=source_file_id,
                            chunk_index=len(chunks),
                        )
                        chunks.append(DocumentChunk(content=content, metadata=metadata))
                        current_chunk_text = []
                        current_chars = 0

                    current_chunk_text.append(para.text)
                    current_chars += len(para.text)

            # Add tables as separate chunks
            for table in doc.tables:
                table_text = []
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        table_text.append(row_text)
                if table_text:
                    content = "[Table]\n" + "\n".join(table_text)
                    metadata = self._create_metadata(
                        file_name=file_name,
                        user_id=user_id,
                        description=description,
                        source_file_id=source_file_id,
                        chunk_index=len(chunks),
                    )
                    chunks.append(DocumentChunk(content=content, metadata=metadata))

            # Flush remaining paragraph text
            if current_chunk_text:
                content = "\n\n".join(current_chunk_text)
                metadata = self._create_metadata(
                    file_name=file_name,
                    user_id=user_id,
                    description=description,
                    source_file_id=source_file_id,
                    chunk_index=len(chunks),
                )
                chunks.append(DocumentChunk(content=content, metadata=metadata))

            # If no chunks were created, create one from raw text
            if not chunks and raw_text.strip():
                metadata = self._create_metadata(
                    file_name=file_name,
                    user_id=user_id,
                    description=description,
                    source_file_id=source_file_id,
                )
                chunks.append(DocumentChunk(content=raw_text.strip(), metadata=metadata))

            # Update total_chunks
            for chunk in chunks:
                chunk.metadata.total_chunks = len(chunks)

            return ParsedDocument(
                file_name=file_name,
                file_type="docx",
                chunks=chunks,
                raw_text=raw_text,
                description=description,
            )

        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            raise ValueError(f"Failed to parse DOCX: {str(e)}")

    def supported_extensions(self) -> list[str]:
        return [".docx", ".doc"]


class XLSXParser(BaseDocumentParser):
    """Parser for Excel files using openpyxl.

    Creates a separate document chunk per sheet tab, storing content in
    a structured tabular format.
    """

    def parse(self, file_content: bytes) -> str:
        """Extract text from Excel spreadsheet."""
        try:
            wb = load_workbook(BytesIO(file_content), data_only=True)
            text_parts = []

            for sheet in wb.worksheets:
                sheet_text = [f"[Sheet: {sheet.title}]"]

                for row in sheet.iter_rows(values_only=True):
                    # Filter out empty cells and format row
                    row_values = [
                        str(cell) if cell is not None else ""
                        for cell in row
                    ]
                    row_text = " | ".join(row_values)
                    if row_text.strip(" |"):
                        sheet_text.append(row_text)

                if len(sheet_text) > 1:  # More than just the header
                    text_parts.append("\n".join(sheet_text))

            wb.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"XLSX parsing error: {e}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")

    def parse_to_document(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        source_file_id: str | None = None,
    ) -> ParsedDocument:
        """Parse Excel into structured document with per-sheet chunks."""
        try:
            wb = load_workbook(BytesIO(file_content), data_only=True)
            chunks: list[DocumentChunk] = []
            raw_text = self.parse(file_content)
            description = generate_description(raw_text)

            for sheet in wb.worksheets:
                rows_text: list[str] = []
                header_row = None

                for row_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                    row_values = [
                        str(cell) if cell is not None else ""
                        for cell in row
                    ]
                    row_text = " | ".join(row_values)
                    if row_text.strip(" |"):
                        if row_idx == 0:
                            header_row = row_text
                        rows_text.append(row_text)

                if rows_text:
                    sheet_content = f"[Sheet: {sheet.title}]\n"
                    if header_row:
                        sheet_content += f"Headers: {header_row}\n"
                    sheet_content += "\n".join(rows_text)

                    metadata = self._create_metadata(
                        file_name=file_name,
                        user_id=user_id,
                        description=description,
                        source_file_id=source_file_id,
                        chunk_index=len(chunks),
                        sheet_name=sheet.title,
                    )
                    chunks.append(DocumentChunk(content=sheet_content, metadata=metadata))

            wb.close()

            # If no chunks, create one from raw text
            if not chunks and raw_text.strip():
                metadata = self._create_metadata(
                    file_name=file_name,
                    user_id=user_id,
                    description=description,
                    source_file_id=source_file_id,
                )
                chunks.append(DocumentChunk(content=raw_text.strip(), metadata=metadata))

            # Update total_chunks
            for chunk in chunks:
                chunk.metadata.total_chunks = len(chunks)

            return ParsedDocument(
                file_name=file_name,
                file_type="xlsx",
                chunks=chunks,
                raw_text=raw_text,
                description=description,
            )

        except Exception as e:
            logger.error(f"XLSX parsing error: {e}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")

    def supported_extensions(self) -> list[str]:
        return [".xlsx", ".xls"]


class PPTXParser(BaseDocumentParser):
    """Parser for PowerPoint files using python-pptx."""

    def parse(self, file_content: bytes) -> str:
        """Extract text from PowerPoint presentation."""
        try:
            prs = Presentation(BytesIO(file_content))
            text_parts = []

            for i, slide in enumerate(prs.slides, 1):
                slide_text = [f"[Slide {i}]"]

                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text)

                    # Extract text from tables
                    if shape.has_table:
                        table = shape.table
                        for row in table.rows:
                            row_text = " | ".join(
                                cell.text.strip()
                                for cell in row.cells
                                if cell.text.strip()
                            )
                            if row_text:
                                slide_text.append(row_text)

                if len(slide_text) > 1:  # More than just the slide number
                    text_parts.append("\n".join(slide_text))

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"PPTX parsing error: {e}")
            raise ValueError(f"Failed to parse PowerPoint file: {str(e)}")

    def parse_to_document(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        source_file_id: str | None = None,
    ) -> ParsedDocument:
        """Parse PowerPoint into structured document with per-slide chunks."""
        try:
            prs = Presentation(BytesIO(file_content))
            chunks: list[DocumentChunk] = []
            raw_text = self.parse(file_content)
            description = generate_description(raw_text)

            for i, slide in enumerate(prs.slides, 1):
                slide_content_parts: list[str] = []

                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_content_parts.append(shape.text)

                    if shape.has_table:
                        table = shape.table
                        for row in table.rows:
                            row_text = " | ".join(
                                cell.text.strip()
                                for cell in row.cells
                                if cell.text.strip()
                            )
                            if row_text:
                                slide_content_parts.append(row_text)

                if slide_content_parts:
                    content = f"[Slide {i}]\n" + "\n".join(slide_content_parts)
                    metadata = self._create_metadata(
                        file_name=file_name,
                        user_id=user_id,
                        description=description,
                        source_file_id=source_file_id,
                        chunk_index=len(chunks),
                        page_number=i,
                    )
                    chunks.append(DocumentChunk(content=content, metadata=metadata))

            # If no chunks, create one from raw text
            if not chunks and raw_text.strip():
                metadata = self._create_metadata(
                    file_name=file_name,
                    user_id=user_id,
                    description=description,
                    source_file_id=source_file_id,
                )
                chunks.append(DocumentChunk(content=raw_text.strip(), metadata=metadata))

            # Update total_chunks
            for chunk in chunks:
                chunk.metadata.total_chunks = len(chunks)

            return ParsedDocument(
                file_name=file_name,
                file_type="pptx",
                chunks=chunks,
                raw_text=raw_text,
                description=description,
            )

        except Exception as e:
            logger.error(f"PPTX parsing error: {e}")
            raise ValueError(f"Failed to parse PowerPoint file: {str(e)}")

    def supported_extensions(self) -> list[str]:
        return [".pptx", ".ppt"]


class ParserFactory:
    """Factory for getting document parsers by file type."""

    _parsers: dict[str, BaseDocumentParser] = {}

    @classmethod
    def register(cls, parser: BaseDocumentParser) -> None:
        """Register a parser for its supported extensions."""
        for ext in parser.supported_extensions():
            cls._parsers[ext.lower()] = parser

    @classmethod
    def get_parser(cls, file_extension: str) -> BaseDocumentParser:
        """Get parser for file extension.

        Args:
            file_extension: File extension (e.g., ".pdf")

        Returns:
            BaseDocumentParser instance

        Raises:
            ValueError: If no parser exists for extension
        """
        ext = file_extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        if ext not in cls._parsers:
            raise ValueError(f"Unsupported file type: {ext}")

        return cls._parsers[ext]

    @classmethod
    def parse_file(cls, file_content: bytes, file_extension: str) -> str:
        """Parse file content using appropriate parser.

        Args:
            file_content: Raw file bytes
            file_extension: File extension

        Returns:
            Extracted text content
        """
        parser = cls.get_parser(file_extension)
        return parser.parse(file_content)

    @classmethod
    def parse_file_to_document(
        cls,
        file_content: bytes,
        file_extension: str,
        file_name: str,
        user_id: str,
        source_file_id: str | None = None,
    ) -> ParsedDocument:
        """Parse file content into a structured ParsedDocument.

        Args:
            file_content: Raw file bytes
            file_extension: File extension
            file_name: Original filename
            user_id: Owner identifier for search filtering
            source_file_id: Optional reference to source_files table

        Returns:
            ParsedDocument with chunks and metadata
        """
        parser = cls.get_parser(file_extension)
        return parser.parse_to_document(
            file_content=file_content,
            file_name=file_name,
            user_id=user_id,
            source_file_id=source_file_id,
        )


# Register all parsers
ParserFactory.register(PDFParser())
ParserFactory.register(DOCXParser())
ParserFactory.register(XLSXParser())
ParserFactory.register(PPTXParser())
