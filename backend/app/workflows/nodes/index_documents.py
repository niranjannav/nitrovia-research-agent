"""Index documents node for the report workflow.

Generates embeddings for parsed document chunks and stores them
in pgvector for similarity search.
"""

import logging
from datetime import datetime

from app.models.document import ParsedDocument
from app.services.document_parser import ParserFactory
from app.services.embedding_service import EmbeddingService
from app.services.supabase import get_supabase_client
from app.workflows.state import (
    ReportWorkflowState,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
)

logger = logging.getLogger(__name__)


async def index_documents_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Index parsed document chunks into pgvector.

    Takes the parsed documents from state, generates embeddings, and
    stores them in the document_chunks table for similarity search.
    Skips files that are already indexed.

    Args:
        state: Current workflow state with parsed documents

    Returns:
        Updated state with indexing status
    """
    report_id = state["report_id"]
    user_id = state["user_id"]
    started_at = datetime.utcnow()
    parsed_documents: list[ParsedDocument] = state.get("parsed_documents", [])

    logger.info(
        f"[WORKFLOW] Report {report_id} | INDEXING | "
        f"Indexing {len(parsed_documents)} documents..."
    )

    state = update_progress(
        state,
        WorkflowStep.INDEXING,
        22,
        "Indexing documents for search...",
    )

    if not parsed_documents:
        logger.warning(f"[WORKFLOW] Report {report_id} | INDEXING | No documents to index")
        state = mark_step_complete(state, WorkflowStep.INDEXING, started_at)
        return state

    try:
        embedding_service = EmbeddingService()

        # Check which files are already indexed
        indexed_ids = await embedding_service.get_indexed_file_ids(user_id)
        total_chunks_indexed = 0

        for parsed_doc in parsed_documents:
            source_file_id = (
                parsed_doc.chunks[0].metadata.source_file_id
                if parsed_doc.chunks
                else None
            )

            # Skip if already indexed
            if source_file_id and source_file_id in indexed_ids:
                logger.info(
                    f"[WORKFLOW] Report {report_id} | INDEXING | "
                    f"Skipping already indexed: {parsed_doc.file_name}"
                )
                continue

            try:
                count = await embedding_service.index_document(parsed_doc)
                total_chunks_indexed += count
                logger.info(
                    f"[WORKFLOW] Report {report_id} | INDEXING | "
                    f"Indexed {count} chunks from {parsed_doc.file_name}"
                )
            except Exception as e:
                logger.error(
                    f"[WORKFLOW] Report {report_id} | INDEXING | "
                    f"Failed to index {parsed_doc.file_name}: {e}"
                )
                # Continue with other documents - indexing failure is non-fatal

        logger.info(
            f"[WORKFLOW] Report {report_id} | INDEXING | COMPLETED | "
            f"Indexed {total_chunks_indexed} total chunks"
        )

        state = update_progress(state, WorkflowStep.INDEXING, 25, "Documents indexed")
        state = mark_step_complete(state, WorkflowStep.INDEXING, started_at)
        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | INDEXING | FAILED | {e}")
        # Indexing failure is non-fatal - workflow can continue with raw documents
        logger.warning(
            f"[WORKFLOW] Report {report_id} | INDEXING | "
            "Continuing without indexing, will use raw document context"
        )
        state = mark_step_complete(state, WorkflowStep.INDEXING, started_at)
        return state
