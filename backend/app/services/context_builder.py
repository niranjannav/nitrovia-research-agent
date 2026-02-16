"""Context builder for preparing LLM input from documents."""

import logging
from dataclasses import dataclass
from pathlib import Path

from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_summarization_prompt() -> str:
    """Load the summarization prompt template."""
    prompt_file = PROMPTS_DIR / "context_summarization.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")

    # Fallback prompt
    return """Summarize this document comprehensively, preserving:
- Key facts and figures
- Main arguments and conclusions
- Important quotes or data points
- Structure and flow of ideas

Be thorough but concise. Maintain the document's original meaning and intent.

DOCUMENT: {filename}
---
{content}"""


@dataclass
class DocumentContext:
    """Parsed document with token count."""

    file_name: str
    content: str
    token_count: int


@dataclass
class PreparedContext:
    """Prepared context ready for LLM."""

    documents: list[DocumentContext]
    total_tokens: int
    was_summarized: bool
    combined_content: str


class ContextBuilder:
    """Builds and optimizes context from parsed documents for LLM input."""

    MAX_CONTEXT_TOKENS = 150_000  # Leave room for output
    SUMMARIZE_THRESHOLD = 100_000
    SUMMARIZE_DOC_THRESHOLD = 10_000  # Summarize individual docs over this

    def __init__(self, anthropic_api_key: str):
        """Initialize with Anthropic client for summarization."""
        self.client = Anthropic(api_key=anthropic_api_key)

    def prepare(
        self,
        documents: list[tuple[str, str]],  # (filename, content)
    ) -> PreparedContext:
        """
        Prepare documents for LLM context.

        Args:
            documents: List of (filename, content) tuples

        Returns:
            PreparedContext with optimized content
        """
        # Count tokens for each document
        doc_contexts = []
        total_tokens = 0

        for filename, content in documents:
            tokens = self._estimate_tokens(content)
            doc_contexts.append(
                DocumentContext(
                    file_name=filename,
                    content=content,
                    token_count=tokens,
                )
            )
            total_tokens += tokens

        logger.info(f"Total tokens before optimization: {total_tokens}")

        # Summarize if needed
        was_summarized = False
        if total_tokens > self.SUMMARIZE_THRESHOLD:
            logger.info("Context exceeds threshold, summarizing documents...")
            doc_contexts = self._summarize_documents(doc_contexts)
            was_summarized = True
            total_tokens = sum(d.token_count for d in doc_contexts)
            logger.info(f"Total tokens after summarization: {total_tokens}")

        # Combine into single context
        combined_content = self._combine_documents(doc_contexts)

        return PreparedContext(
            documents=doc_contexts,
            total_tokens=total_tokens,
            was_summarized=was_summarized,
            combined_content=combined_content,
        )

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses rough estimate of 4 characters per token.
        """
        return len(text) // 4

    def _summarize_documents(
        self,
        docs: list[DocumentContext],
    ) -> list[DocumentContext]:
        """Summarize large documents to reduce context size."""
        summarized = []

        for doc in docs:
            if doc.token_count > self.SUMMARIZE_DOC_THRESHOLD:
                logger.info(f"Summarizing {doc.file_name} ({doc.token_count} tokens)")
                summary = self._summarize_single(doc.content, doc.file_name)
                summarized.append(
                    DocumentContext(
                        file_name=doc.file_name,
                        content=summary,
                        token_count=self._estimate_tokens(summary),
                    )
                )
            else:
                summarized.append(doc)

        return summarized

    def _summarize_single(self, content: str, filename: str) -> str:
        """
        Summarize a single document using Claude Haiku.

        Uses Haiku for cost-effective summarization.
        """
        try:
            # Load prompt from external file
            prompt_template = load_summarization_prompt()
            prompt = prompt_template.format(filename=filename, content=content)

            logger.info(f"[CONTEXT] Summarizing document: {filename}")

            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )

            logger.info(f"[CONTEXT] Document summarized: {filename}")
            return f"[Summarized from {filename}]\n\n{response.content[0].text}"

        except Exception as e:
            logger.error(f"[CONTEXT] Failed to summarize {filename}: {e}")
            # Return truncated content as fallback
            max_chars = self.SUMMARIZE_DOC_THRESHOLD * 4
            return f"[Truncated: {filename}]\n\n{content[:max_chars]}..."

    def _combine_documents(self, docs: list[DocumentContext]) -> str:
        """Combine all documents into a single context string."""
        parts = []

        for doc in docs:
            parts.append(f"=== DOCUMENT: {doc.file_name} ===\n\n{doc.content}")

        return "\n\n" + "=" * 50 + "\n\n".join(parts)
