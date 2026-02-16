"""Build context node for the report workflow.

Prepares documents for LLM input, including summarization if needed.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.llm import ModelGateway, GatewayConfig, TaskType
from app.workflows.state import (
    DocumentContext,
    PreparedContext,
    ReportWorkflowState,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
    update_token_metrics,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"

# Context thresholds - lowered to stay within per-minute rate limits
# (org rate limit is 30K tokens/min for Sonnet, 50K for Haiku)
MAX_CONTEXT_TOKENS = 25_000
SUMMARIZE_THRESHOLD = 20_000
SUMMARIZE_DOC_THRESHOLD = 8_000


def _load_summarization_prompt() -> str:
    """Load the summarization prompt template."""
    prompt_file = PROMPTS_DIR / "context_summarization.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")

    return """Summarize this document comprehensively, preserving:
- Key facts and figures
- Main arguments and conclusions
- Important quotes or data points
- Structure and flow of ideas

Be thorough but concise. Maintain the document's original meaning and intent.

DOCUMENT: {filename}
---
{content}"""


async def build_context_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Build optimized context from parsed documents.

    Estimates tokens, summarizes large documents if needed, and combines
    all documents into a single context string.

    Args:
        state: Current workflow state with parsed documents

    Returns:
        Updated state with prepared context
    """
    report_id = state["report_id"]
    documents = state.get("documents", [])
    started_at = datetime.utcnow()

    logger.info(f"[WORKFLOW] Report {report_id} | CONTEXT | Building context from {len(documents)} documents...")

    state = update_progress(
        state,
        WorkflowStep.BUILDING_CONTEXT,
        25,
        "Building context...",
    )

    if not documents:
        return mark_failed(state, "No documents available for context building")

    try:
        # Create gateway for summarization
        gateway_config = GatewayConfig(
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=getattr(settings, "openai_api_key", None),
        )
        gateway = ModelGateway(gateway_config)

        # Estimate tokens for each document
        doc_contexts: list[DocumentContext] = []
        total_tokens = 0

        for filename, content in documents:
            tokens = gateway.count_tokens(content, TaskType.SUMMARIZATION)
            doc_contexts.append(
                DocumentContext(
                    file_name=filename,
                    content=content,
                    token_count=tokens,
                )
            )
            total_tokens += tokens

        logger.info(f"[WORKFLOW] Report {report_id} | CONTEXT | Total tokens before optimization: {total_tokens}")

        # Summarize if needed
        was_summarized = False
        total_input_tokens = 0
        total_output_tokens = 0

        if total_tokens > SUMMARIZE_THRESHOLD:
            logger.info(f"[WORKFLOW] Report {report_id} | CONTEXT | Threshold exceeded, summarizing...")
            doc_contexts, input_toks, output_toks = await _summarize_documents(
                gateway, doc_contexts, report_id
            )
            was_summarized = True
            total_tokens = sum(d.token_count for d in doc_contexts)
            total_input_tokens += input_toks
            total_output_tokens += output_toks
            logger.info(f"[WORKFLOW] Report {report_id} | CONTEXT | Tokens after summarization: {total_tokens}")

        # Combine into single context
        combined_content = _combine_documents(doc_contexts)

        prepared_context = PreparedContext(
            documents=doc_contexts,
            total_tokens=total_tokens,
            was_summarized=was_summarized,
            combined_content=combined_content,
        )

        logger.info(
            f"[WORKFLOW] Report {report_id} | CONTEXT | COMPLETED | "
            f"tokens={total_tokens}, summarized={was_summarized}"
        )

        # Update state
        state = {
            **state,
            "prepared_context": prepared_context,
        }

        state = update_token_metrics(state, total_input_tokens, total_output_tokens)
        state = update_progress(state, WorkflowStep.BUILDING_CONTEXT, 30, "Context ready")
        state = mark_step_complete(state, WorkflowStep.BUILDING_CONTEXT, started_at)

        return state

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | CONTEXT | FAILED | {e}")
        return mark_failed(state, f"Context building failed: {e}")


async def _summarize_documents(
    gateway: ModelGateway,
    docs: list[DocumentContext],
    report_id: str,
) -> tuple[list[DocumentContext], int, int]:
    """Summarize large documents.

    Args:
        gateway: Model gateway for LLM calls
        docs: Documents to process
        report_id: Report ID for logging

    Returns:
        Tuple of (summarized documents, total input tokens, total output tokens)
    """
    summarized: list[DocumentContext] = []
    total_input_tokens = 0
    total_output_tokens = 0

    prompt_template = _load_summarization_prompt()

    for doc in docs:
        if doc.token_count > SUMMARIZE_DOC_THRESHOLD:
            logger.info(
                f"[WORKFLOW] Report {report_id} | CONTEXT | "
                f"Summarizing {doc.file_name} ({doc.token_count} tokens)"
            )

            try:
                # Prepare summarization prompt
                prompt = prompt_template.format(
                    filename=doc.file_name,
                    content=doc.content,
                )

                # Call LLM for summarization
                result = await gateway.generate_text(
                    task=TaskType.SUMMARIZATION,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3000,
                )

                summary = f"[Summarized from {doc.file_name}]\n\n{result.content}"
                new_token_count = gateway.count_tokens(summary, TaskType.SUMMARIZATION)

                summarized.append(
                    DocumentContext(
                        file_name=doc.file_name,
                        content=summary,
                        token_count=new_token_count,
                    )
                )

                total_input_tokens += result.usage.input_tokens
                total_output_tokens += result.usage.output_tokens

                logger.info(
                    f"[WORKFLOW] Report {report_id} | CONTEXT | "
                    f"Summarized {doc.file_name}: {doc.token_count} -> {new_token_count} tokens"
                )

            except Exception as e:
                logger.error(
                    f"[WORKFLOW] Report {report_id} | CONTEXT | "
                    f"Summarization failed for {doc.file_name}: {e}"
                )
                # Fall back to truncation
                max_chars = SUMMARIZE_DOC_THRESHOLD * 4
                truncated = f"[Truncated: {doc.file_name}]\n\n{doc.content[:max_chars]}..."
                summarized.append(
                    DocumentContext(
                        file_name=doc.file_name,
                        content=truncated,
                        token_count=SUMMARIZE_DOC_THRESHOLD,
                    )
                )
        else:
            summarized.append(doc)

    return summarized, total_input_tokens, total_output_tokens


def _combine_documents(docs: list[DocumentContext]) -> str:
    """Combine all documents into a single context string.

    Args:
        docs: Documents to combine

    Returns:
        Combined context string
    """
    parts = []

    for doc in docs:
        parts.append(f"=== DOCUMENT: {doc.file_name} ===\n\n{doc.content}")

    return "\n\n" + ("\n\n" + "=" * 50 + "\n\n").join(parts)
