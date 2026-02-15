"""Retrieve context node for the report workflow.

Generates research questions from the title/prompt, performs similarity
search against pgvector, and assembles the retrieved context.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.config import get_settings
from app.models.document import ParsedDocument
from app.services.embedding_service import EmbeddingService
from app.services.research_planner import ResearchPlanner
from app.workflows.state import (
    DocumentContext,
    PreparedContext,
    ReportWorkflowState,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Number of top results per question
TOP_K_PER_QUESTION = 5
# Delay between similarity search queries (seconds)
SEARCH_DELAY_SECONDS = 0.5
# Maximum tokens to include in retrieved context (stay well under rate limits)
MAX_CONTEXT_TOKENS = 25_000
# Maximum characters for fallback raw document context
MAX_RAW_CONTEXT_CHARS = 80_000


async def retrieve_context_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Generate research questions and retrieve relevant context via similarity search.

    This node:
    1. Takes the report title + custom_instructions
    2. Generates expanded research questions via ResearchPlanner
    3. Performs similarity search for each question against pgvector
    4. Deduplicates and assembles the retrieved chunks into prepared context

    Falls back to raw document content if similarity search is unavailable.

    Args:
        state: Current workflow state with parsed documents and config

    Returns:
        Updated state with research_questions and prepared_context
    """
    report_id = state["report_id"]
    user_id = state["user_id"]
    config = state.get("config", {})
    parsed_documents: list[ParsedDocument] = state.get("parsed_documents", [])
    documents = state.get("documents", [])
    started_at = datetime.utcnow()

    title = config.get("title", "Research Report")
    custom_instructions = config.get("custom_instructions")

    logger.info(
        f"[WORKFLOW] Report {report_id} | RETRIEVE | "
        f"Starting context retrieval for: {title}"
    )

    state = update_progress(
        state,
        WorkflowStep.BUILDING_CONTEXT,
        27,
        "Planning research questions...",
    )

    try:
        # Step 1: Generate research questions
        planner = ResearchPlanner()

        # Collect file descriptions for context
        file_descriptions = [
            doc.description for doc in parsed_documents if doc.description
        ]

        research_plan = await planner.generate_research_plan(
            title=title,
            custom_instructions=custom_instructions,
            file_descriptions=file_descriptions,
        )

        logger.info(
            f"[WORKFLOW] Report {report_id} | RETRIEVE | "
            f"Generated {len(research_plan.questions)} research questions"
        )

        # Store questions in state
        state = {**state, "research_questions": research_plan.questions}

        state = update_progress(
            state,
            WorkflowStep.BUILDING_CONTEXT,
            28,
            "Searching for relevant content...",
        )

        # Step 2: Perform similarity search for each question
        embedding_service = EmbeddingService()

        # Get source file IDs to restrict search scope
        source_file_ids = []
        for doc in parsed_documents:
            if doc.chunks:
                sfid = doc.chunks[0].metadata.source_file_id
                if sfid:
                    source_file_ids.append(sfid)

        all_results: list[dict[str, Any]] = []
        seen_contents: set[int] = set()

        for q_idx, question in enumerate(research_plan.questions):
            # Delay between search calls to avoid embedding rate limits
            if q_idx > 0:
                await asyncio.sleep(SEARCH_DELAY_SECONDS)

            try:
                results = await embedding_service.similarity_search(
                    query=question,
                    user_id=user_id,
                    top_k=TOP_K_PER_QUESTION,
                    source_file_ids=source_file_ids if source_file_ids else None,
                )

                for result in results:
                    content = result.get("content", "")
                    # Deduplicate by content hash
                    content_key = hash(content)
                    if content_key not in seen_contents:
                        seen_contents.add(content_key)
                        all_results.append(result)

            except Exception as e:
                logger.warning(
                    f"[WORKFLOW] Report {report_id} | RETRIEVE | "
                    f"Search failed for question: {e}"
                )

        logger.info(
            f"[WORKFLOW] Report {report_id} | RETRIEVE | "
            f"Retrieved {len(all_results)} unique chunks from similarity search"
        )

        # Step 3: Build prepared context from retrieved results
        if all_results:
            prepared_context = _build_context_from_results(all_results, parsed_documents)
        else:
            # Fallback to raw documents if no search results
            logger.warning(
                f"[WORKFLOW] Report {report_id} | RETRIEVE | "
                "No search results, falling back to raw document context"
            )
            prepared_context = _build_context_from_raw_documents(
                documents, parsed_documents
            )

        state = {
            **state,
            "prepared_context": prepared_context,
        }

        logger.info(
            f"[WORKFLOW] Report {report_id} | RETRIEVE | COMPLETED | "
            f"Context tokens={prepared_context.total_tokens}, "
            f"docs={len(prepared_context.documents)}"
        )

        state = update_progress(
            state, WorkflowStep.BUILDING_CONTEXT, 30, "Context retrieved"
        )
        state = mark_step_complete(state, WorkflowStep.BUILDING_CONTEXT, started_at)

        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | RETRIEVE | FAILED | {e}")
        # Fall back to raw document context on any error
        logger.warning(
            f"[WORKFLOW] Report {report_id} | RETRIEVE | "
            "Falling back to raw document context"
        )
        try:
            prepared_context = _build_context_from_raw_documents(
                documents, parsed_documents
            )
            state = {
                **state,
                "prepared_context": prepared_context,
            }
            state = update_progress(
                state, WorkflowStep.BUILDING_CONTEXT, 30, "Context ready (fallback)"
            )
            state = mark_step_complete(state, WorkflowStep.BUILDING_CONTEXT, started_at)
            return state
        except Exception:
            return mark_failed(state, f"Context retrieval failed: {e}")


def _build_context_from_results(
    results: list[dict[str, Any]],
    parsed_documents: list[ParsedDocument],
) -> PreparedContext:
    """Build PreparedContext from similarity search results.

    Caps total context at MAX_CONTEXT_TOKENS to avoid exceeding rate limits
    when passed to the LLM for report generation.

    Args:
        results: List of search result dicts with 'content' and 'metadata'
        parsed_documents: Original parsed documents for reference

    Returns:
        PreparedContext ready for LLM
    """
    doc_contexts: list[DocumentContext] = []
    total_tokens = 0

    # Group results by source file for better organization
    file_groups: dict[str, list[str]] = {}
    for result in results:
        metadata = result.get("metadata", {})
        file_name = metadata.get("file_name", "Unknown")
        content = result.get("content", "")
        if content:
            if file_name not in file_groups:
                file_groups[file_name] = []
            file_groups[file_name].append(content)

    for file_name, contents in file_groups.items():
        combined = "\n\n---\n\n".join(contents)
        token_count = len(combined) // 4  # Rough estimate

        # Stop adding more content if we'd exceed the budget
        if total_tokens + token_count > MAX_CONTEXT_TOKENS:
            # Truncate this document to fit remaining budget
            remaining_tokens = MAX_CONTEXT_TOKENS - total_tokens
            if remaining_tokens > 500:  # Only add if meaningful amount fits
                max_chars = remaining_tokens * 4
                combined = combined[:max_chars]
                token_count = remaining_tokens
            else:
                logger.info(
                    f"Skipping {file_name} to stay within context budget "
                    f"({total_tokens}/{MAX_CONTEXT_TOKENS} tokens used)"
                )
                continue

        doc_contexts.append(
            DocumentContext(
                file_name=file_name,
                content=combined,
                token_count=token_count,
            )
        )
        total_tokens += token_count

    # Build combined content
    parts = []
    for doc in doc_contexts:
        parts.append(f"=== DOCUMENT: {doc.file_name} ===\n\n{doc.content}")

    combined_content = "\n\n" + ("\n\n" + "=" * 50 + "\n\n").join(parts)

    return PreparedContext(
        documents=doc_contexts,
        total_tokens=total_tokens,
        was_summarized=False,
        combined_content=combined_content,
    )


def _build_context_from_raw_documents(
    documents: list[tuple[str, str]],
    parsed_documents: list[ParsedDocument],
) -> PreparedContext:
    """Build PreparedContext from raw document tuples (fallback).

    Truncates content per file and in total to stay within
    MAX_CONTEXT_TOKENS, avoiding rate limit errors during report generation.

    Args:
        documents: List of (filename, content) tuples
        parsed_documents: Original parsed documents

    Returns:
        PreparedContext ready for LLM
    """
    doc_contexts: list[DocumentContext] = []
    total_tokens = 0

    # Prefer parsed_documents if available
    sources = []
    if parsed_documents:
        sources = [(doc.file_name, doc.raw_text) for doc in parsed_documents]
    elif documents:
        sources = documents

    # Calculate per-file char budget to distribute evenly
    num_files = len(sources) or 1
    per_file_char_budget = min(
        MAX_RAW_CONTEXT_CHARS // num_files,
        MAX_CONTEXT_TOKENS * 4 // num_files,
    )

    for file_name, content in sources:
        # Truncate if needed
        if len(content) > per_file_char_budget:
            content = content[:per_file_char_budget] + f"\n\n[... truncated, {len(content) - per_file_char_budget} chars omitted ...]"
            logger.info(
                f"Truncated {file_name} to {per_file_char_budget} chars "
                f"for context budget"
            )

        token_count = len(content) // 4

        if total_tokens + token_count > MAX_CONTEXT_TOKENS:
            remaining = MAX_CONTEXT_TOKENS - total_tokens
            if remaining > 500:
                content = content[: remaining * 4]
                token_count = remaining
            else:
                break

        doc_contexts.append(
            DocumentContext(
                file_name=file_name,
                content=content,
                token_count=token_count,
            )
        )
        total_tokens += token_count

    parts = []
    for doc in doc_contexts:
        parts.append(f"=== DOCUMENT: {doc.file_name} ===\n\n{doc.content}")

    combined_content = "\n\n" + ("\n\n" + "=" * 50 + "\n\n").join(parts)

    return PreparedContext(
        documents=doc_contexts,
        total_tokens=total_tokens,
        was_summarized=True,  # Mark as summarized since content was truncated
        combined_content=combined_content,
    )
