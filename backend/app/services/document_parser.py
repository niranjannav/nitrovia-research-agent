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
    """Enhanced parser for Excel files using openpyxl.

    Extracts structured metadata including:
    - Sheet dimensions and structure
    - Column headers with inferred data types
    - Data samples (first rows)
    - Per-column statistics for numeric fields
    - Formula detection
    - Empty-cell analysis
    """

    # Maximum rows to include as data sample
    MAX_SAMPLE_ROWS = 50
    # Maximum rows to scan for statistics
    MAX_STAT_ROWS = 10_000

    def parse(self, file_content: bytes) -> str:
        """Extract structured text from Excel spreadsheet."""
        try:
            from io import BytesIO
            from statistics import mean, median, stdev

            # Load with data_only=True for computed values
            wb_data = load_workbook(BytesIO(file_content), data_only=True)
            # Load again with formulas to detect formula cells
            try:
                wb_formulas = load_workbook(BytesIO(file_content), data_only=False)
            except Exception:
                wb_formulas = None

            text_parts = []

            for sheet_idx, sheet in enumerate(wb_data.worksheets):
                rows_count = sheet.max_row or 0
                cols_count = sheet.max_column or 0

                if rows_count == 0 or cols_count == 0:
                    continue

                section = [f"[Sheet: {sheet.title} | {rows_count} rows × {cols_count} cols]"]

                # --- Extract headers (first non-empty row) ---
                headers: list[str] = []
                header_row_idx = 1
                for row in sheet.iter_rows(min_row=1, max_row=min(5, rows_count), values_only=True):
                    row_vals = [str(c).strip() if c is not None else "" for c in row]
                    if any(v for v in row_vals):
                        headers = row_vals
                        break
                    header_row_idx += 1

                # --- Infer column data types from first 100 data rows ---
                col_types: list[str] = ["unknown"] * cols_count
                col_values: list[list] = [[] for _ in range(cols_count)]

                data_start = header_row_idx + 1
                scan_end = min(data_start + self.MAX_STAT_ROWS, rows_count + 1)

                for row in sheet.iter_rows(min_row=data_start, max_row=scan_end, values_only=True):
                    for ci, cell in enumerate(row):
                        if ci >= cols_count:
                            break
                        if cell is not None:
                            col_values[ci].append(cell)

                for ci in range(cols_count):
                    vals = col_values[ci]
                    if not vals:
                        col_types[ci] = "empty"
                        continue
                    num_count = sum(1 for v in vals if isinstance(v, (int, float)))
                    str_count = sum(1 for v in vals if isinstance(v, str))
                    if num_count > len(vals) * 0.7:
                        col_types[ci] = "numeric"
                    elif str_count > len(vals) * 0.7:
                        col_types[ci] = "text"
                    else:
                        col_types[ci] = "mixed"

                # --- Headers with types ---
                if headers:
                    header_line = " | ".join(
                        f"{h} ({col_types[i]})" if i < len(col_types) else h
                        for i, h in enumerate(headers)
                    )
                    section.append(f"Headers: {header_line}")

                # --- Data sample ---
                section.append("")
                section.append("Data:")
                sample_end = min(data_start + self.MAX_SAMPLE_ROWS, rows_count + 1)
                for row in sheet.iter_rows(min_row=data_start, max_row=sample_end, values_only=True):
                    row_values = [
                        str(cell) if cell is not None else ""
                        for cell in row
                    ]
                    row_text = " | ".join(row_values)
                    if row_text.strip(" |"):
                        section.append(row_text)

                if rows_count > data_start + self.MAX_SAMPLE_ROWS:
                    section.append(f"... ({rows_count - data_start - self.MAX_SAMPLE_ROWS} more rows)")

                # --- Per-column statistics for numeric columns ---
                stats_lines = []
                for ci in range(cols_count):
                    if col_types[ci] != "numeric":
                        continue
                    nums = [v for v in col_values[ci] if isinstance(v, (int, float))]
                    if len(nums) < 2:
                        continue
                    header_name = headers[ci] if ci < len(headers) and headers[ci] else f"Col{ci+1}"
                    try:
                        stats_lines.append(
                            f"  {header_name}: "
                            f"min={min(nums):.2f}, max={max(nums):.2f}, "
                            f"mean={mean(nums):.2f}, median={median(nums):.2f}, "
                            f"sum={sum(nums):.2f}, stdev={stdev(nums):.2f}, "
                            f"count={len(nums)}"
                        )
                    except Exception:
                        pass

                if stats_lines:
                    section.append("")
                    section.append("Column Statistics:")
                    section.extend(stats_lines)

                # --- Formula detection ---
                if wb_formulas and sheet_idx < len(wb_formulas.worksheets):
                    formula_sheet = wb_formulas.worksheets[sheet_idx]
                    formulas_found = []
                    for row in formula_sheet.iter_rows(
                        min_row=1,
                        max_row=min(rows_count, 200),
                        max_col=cols_count,
                    ):
                        for cell in row:
                            if cell.value and isinstance(cell.value, str) and cell.value.startswith("="):
                                coord = cell.coordinate
                                formulas_found.append(f"  {coord}: {cell.value}")
                                if len(formulas_found) >= 20:
                                    break
                        if len(formulas_found) >= 20:
                            break

                    if formulas_found:
                        section.append("")
                        section.append("Formulas detected:")
                        section.extend(formulas_found)

                # --- Empty-cell analysis ---
                empty_lines = []
                total_data_rows = min(scan_end - data_start, rows_count)
                if total_data_rows > 0:
                    for ci in range(cols_count):
                        empty_count = total_data_rows - len(col_values[ci])
                        if empty_count > 0:
                            pct = (empty_count / total_data_rows) * 100
                            if pct > 10:
                                header_name = headers[ci] if ci < len(headers) and headers[ci] else f"Col{ci+1}"
                                empty_lines.append(f"  {header_name}: {pct:.0f}% empty")

                if empty_lines:
                    section.append("")
                    section.append("Data completeness warnings:")
                    section.extend(empty_lines)

                text_parts.append("\n".join(section))

            wb_data.close()
            if wb_formulas:
                wb_formulas.close()

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"XLSX parsing error: {e}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")

    def supported_extensions(self) -> list[str]:
        return [".xlsx", ".xls"]


class PPTXParser(DocumentParser):
    """Enhanced parser for PowerPoint files using python-pptx.

    Extracts:
    - Slide text content with layout type indicators
    - Speaker notes
    - Table content
    - Media/image placeholders
    - Slide count and structure overview
    """

    def parse(self, file_content: bytes) -> str:
        """Extract structured text from PowerPoint presentation."""
        try:
            from io import BytesIO

            prs = Presentation(BytesIO(file_content))
            text_parts = []
            total_slides = len(prs.slides)

            text_parts.append(f"[Presentation: {total_slides} slides]")

            for i, slide in enumerate(prs.slides, 1):
                slide_text = []

                # Detect layout type
                layout_name = "unknown"
                try:
                    if slide.slide_layout and slide.slide_layout.name:
                        layout_name = slide.slide_layout.name
                except Exception:
                    pass

                slide_text.append(f"[Slide {i}/{total_slides} | Layout: {layout_name}]")

                # Track content types found
                has_images = False
                has_charts = False
                has_tables = False

                for shape in slide.shapes:
                    # Text content
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text)

                    # Table extraction
                    if shape.has_table:
                        has_tables = True
                        table = shape.table
                        table_rows = []
                        for row in table.rows:
                            row_text = " | ".join(
                                cell.text.strip()
                                for cell in row.cells
                                if cell.text.strip()
                            )
                            if row_text:
                                table_rows.append(row_text)
                        if table_rows:
                            slide_text.append("[Table]")
                            slide_text.extend(table_rows)

                    # Image detection
                    if shape.shape_type and shape.shape_type == 13:  # Picture
                        has_images = True

                    # Chart detection
                    if hasattr(shape, "has_chart") and shape.has_chart:
                        has_charts = True

                # Media indicators
                media_notes = []
                if has_images:
                    media_notes.append("contains image(s)")
                if has_charts:
                    media_notes.append("contains chart(s)")
                if has_tables:
                    media_notes.append("contains table(s)")
                if media_notes:
                    slide_text.append(f"[Media: {', '.join(media_notes)}]")

                # Speaker notes
                try:
                    if slide.has_notes_slide and slide.notes_slide:
                        notes_text = slide.notes_slide.notes_text_frame.text.strip()
                        if notes_text:
                            slide_text.append(f"[Speaker Notes: {notes_text}]")
                except Exception:
                    pass

                if len(slide_text) > 1:  # More than just the slide marker
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
