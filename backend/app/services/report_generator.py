"""Report generation orchestration service."""

import logging
import time
from datetime import datetime, timezone

from app.config import get_settings
from app.models.schemas import GeneratedPresentation, GeneratedReport
from app.services.context_builder import ContextBuilder
from app.services.document_parser import ParserFactory
from app.services.llm_service import LLMService
from app.services.pdf_renderer import PDFRenderer
from app.services.docx_renderer import DOCXRenderer
from app.services.pptx_renderer import PPTXRenderer
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)
settings = get_settings()


class ReportGeneratorService:
    """Orchestrates the full report generation pipeline."""

    def __init__(self):
        """Initialize all required services."""
        self.supabase = get_supabase_client()
        self.llm_service = LLMService(settings.anthropic_api_key)
        self.context_builder = ContextBuilder(settings.anthropic_api_key)
        self.pdf_renderer = PDFRenderer()
        self.docx_renderer = DOCXRenderer()
        self.pptx_renderer = PPTXRenderer()

    async def generate(self, report_id: str, user_id: str) -> None:
        """
        Execute full report generation pipeline.

        Args:
            report_id: Report UUID
            user_id: User UUID
        """
        start_time = time.time()
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            # Get report configuration
            report = self.supabase.table("reports").select("*").eq(
                "id", report_id
            ).single().execute()

            if not report.data:
                raise ValueError(f"Report not found: {report_id}")

            report_config = report.data
            self._update_status(report_id, "processing", 5, "Starting generation...")
            self._log_step(report_id, "started", "started", "Report generation started")

            # Step 1: Parse source documents (0-20%)
            self._update_status(report_id, "processing", 10, "Parsing source documents...")
            documents = await self._parse_documents(report_id, user_id)
            self._update_status(report_id, "processing", 20, "Documents parsed")
            self._log_step(report_id, "parsing", "completed", f"Parsed {len(documents)} documents")

            # Step 2: Build context (20-30%)
            self._update_status(report_id, "processing", 25, "Building context...")
            prepared_context = self.context_builder.prepare(documents)
            self._update_status(report_id, "processing", 30, "Context ready")
            self._log_step(
                report_id, "context_build", "completed",
                f"Context built: {prepared_context.total_tokens} tokens, summarized: {prepared_context.was_summarized}"
            )

            # Step 3: Generate report (30-60%)
            self._update_status(report_id, "processing", 35, "Generating report content...")
            generated_report = self.llm_service.generate_report(
                context=prepared_context.combined_content,
                custom_instructions=report_config.get("custom_instructions"),
                detail_level=report_config.get("detail_level", "standard"),
                title_hint=report_config.get("title"),
            )
            self._update_status(report_id, "processing", 60, "Report content generated")
            self._log_step(report_id, "llm_report", "completed", "Report generated successfully")

            # Step 4: Generate presentation if PPTX requested (60-80%)
            generated_presentation = None
            output_formats = report_config.get("output_formats", ["pdf"])

            if "pptx" in output_formats:
                self._update_status(report_id, "processing", 65, "Creating presentation slides...")
                generated_presentation = self.llm_service.generate_presentation(
                    report=generated_report,
                    slide_count_min=report_config.get("slide_count_min", 10),
                    slide_count_max=report_config.get("slide_count_max", 15),
                )
                self._update_status(report_id, "processing", 80, "Presentation created")
                self._log_step(
                    report_id, "llm_presentation", "completed",
                    f"Presentation generated: {len(generated_presentation.slides)} slides"
                )
            else:
                self._update_status(report_id, "processing", 80, "Skipping presentation")

            # Step 5: Render output files (80-95%)
            self._update_status(report_id, "processing", 82, "Rendering output files...")
            output_files = await self._render_outputs(
                report_id=report_id,
                user_id=user_id,
                generated_report=generated_report,
                generated_presentation=generated_presentation,
                output_formats=output_formats,
            )
            self._update_status(report_id, "processing", 95, "Files rendered")
            self._log_step(
                report_id, "rendering", "completed",
                f"Rendered {len(output_files)} output files"
            )

            # Step 6: Finalize (95-100%)
            generation_time = int(time.time() - start_time)

            # Update report with generated content and output files
            self.supabase.table("reports").update({
                "status": "completed",
                "progress": 100,
                "generated_content": {
                    "report": generated_report.model_dump(),
                    "presentation": generated_presentation.model_dump() if generated_presentation else None,
                },
                "output_files": output_files,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "generation_time_seconds": generation_time,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "title": generated_report.title,  # Update with generated title
            }).eq("id", report_id).execute()

            self._log_step(
                report_id, "completed", "completed",
                f"Report completed in {generation_time}s"
            )

            logger.info(f"Report {report_id} completed successfully in {generation_time}s")

        except Exception as e:
            logger.error(f"Report generation failed for {report_id}: {e}")
            self._update_status(report_id, "failed", 0, str(e))
            self._log_step(report_id, "error", "failed", str(e))
            raise

    async def _parse_documents(
        self,
        report_id: str,
        user_id: str,
    ) -> list[tuple[str, str]]:
        """Parse all source documents for the report."""
        # Get source files
        source_files = self.supabase.table("source_files").select("*").eq(
            "report_id", report_id
        ).execute()

        documents = []

        for sf in source_files.data:
            try:
                # Download file from storage
                storage_path = sf.get("storage_path")
                if not storage_path:
                    continue

                file_content = self.supabase.storage.from_(
                    settings.upload_bucket
                ).download(storage_path)

                # Parse file
                file_type = sf.get("file_type", "")
                parsed_content = ParserFactory.parse_file(file_content, file_type)

                # Update source file record
                self.supabase.table("source_files").update({
                    "parsed_content": parsed_content[:50000],  # Store truncated for reference
                    "parsing_status": "completed",
                }).eq("id", sf["id"]).execute()

                documents.append((sf["file_name"], parsed_content))

            except Exception as e:
                logger.error(f"Failed to parse {sf.get('file_name')}: {e}")
                self.supabase.table("source_files").update({
                    "parsing_status": "failed",
                    "parsing_error": str(e),
                }).eq("id", sf["id"]).execute()

        if not documents:
            raise ValueError("No documents could be parsed")

        return documents

    async def _render_outputs(
        self,
        report_id: str,
        user_id: str,
        generated_report: GeneratedReport,
        generated_presentation: GeneratedPresentation | None,
        output_formats: list[str],
    ) -> list[dict]:
        """Render and upload output files."""
        output_files = []

        for fmt in output_formats:
            try:
                if fmt == "pdf":
                    content = self.pdf_renderer.render(generated_report)
                    content_type = "application/pdf"
                    extension = "pdf"

                elif fmt == "docx":
                    content = self.docx_renderer.render(generated_report)
                    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    extension = "docx"

                elif fmt == "pptx" and generated_presentation:
                    content = self.pptx_renderer.render(generated_presentation)
                    content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    extension = "pptx"

                else:
                    continue

                # Upload to storage
                storage_path = f"{user_id}/{report_id}/output.{extension}"

                self.supabase.storage.from_(settings.output_bucket).upload(
                    storage_path,
                    content.getvalue(),
                    {"content-type": content_type},
                )

                # Generate signed URL for download
                signed_url = self.supabase.storage.from_(
                    settings.output_bucket
                ).create_signed_url(storage_path, 3600 * 24 * 7)  # 7 days

                output_files.append({
                    "format": fmt,
                    "storage_path": storage_path,
                    "download_url": signed_url.get("signedURL"),
                    "expires_at": datetime.now(timezone.utc).isoformat(),
                })

            except Exception as e:
                logger.error(f"Failed to render {fmt}: {e}")

        return output_files

    def _update_status(
        self,
        report_id: str,
        status: str,
        progress: int,
        message: str,
    ) -> None:
        """Update report status and progress."""
        self.supabase.table("reports").update({
            "status": status,
            "progress": progress,
        }).eq("id", report_id).execute()

    def _log_step(
        self,
        report_id: str,
        step: str,
        status: str,
        message: str,
    ) -> None:
        """Log a generation step."""
        try:
            self.supabase.table("generation_logs").insert({
                "report_id": report_id,
                "step": step,
                "status": status,
                "message": message,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log step: {e}")
