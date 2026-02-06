"""Document parsing service for multiple file formats."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

import fitz  # PyMuPDF
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

logger = logging.getLogger(__name__)


class DocumentParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_content: bytes) -> str:
        """
        Extract text content from document.

        Args:
            file_content: Raw file bytes

        Returns:
            Extracted text content
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        pass


class PDFParser(DocumentParser):
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

    def supported_extensions(self) -> list[str]:
        return [".pdf"]


class DOCXParser(DocumentParser):
    """Parser for DOCX files using python-docx."""

    def parse(self, file_content: bytes) -> str:
        """Extract text from DOCX."""
        try:
            from io import BytesIO

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

    def supported_extensions(self) -> list[str]:
        return [".docx", ".doc"]


class XLSXParser(DocumentParser):
    """Parser for Excel files using openpyxl."""

    def parse(self, file_content: bytes) -> str:
        """Extract text from Excel spreadsheet."""
        try:
            from io import BytesIO

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

    def supported_extensions(self) -> list[str]:
        return [".xlsx", ".xls"]


class PPTXParser(DocumentParser):
    """Parser for PowerPoint files using python-pptx."""

    def parse(self, file_content: bytes) -> str:
        """Extract text from PowerPoint presentation."""
        try:
            from io import BytesIO

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

    def supported_extensions(self) -> list[str]:
        return [".pptx", ".ppt"]


class ParserFactory:
    """Factory for getting document parsers by file type."""

    _parsers: dict[str, DocumentParser] = {}

    @classmethod
    def register(cls, parser: DocumentParser) -> None:
        """Register a parser for its supported extensions."""
        for ext in parser.supported_extensions():
            cls._parsers[ext.lower()] = parser

    @classmethod
    def get_parser(cls, file_extension: str) -> DocumentParser:
        """
        Get parser for file extension.

        Args:
            file_extension: File extension (e.g., ".pdf")

        Returns:
            DocumentParser instance

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
        """
        Parse file content using appropriate parser.

        Args:
            file_content: Raw file bytes
            file_extension: File extension

        Returns:
            Extracted text content
        """
        parser = cls.get_parser(file_extension)
        return parser.parse(file_content)


# Register all parsers
ParserFactory.register(PDFParser())
ParserFactory.register(DOCXParser())
ParserFactory.register(XLSXParser())
ParserFactory.register(PPTXParser())
