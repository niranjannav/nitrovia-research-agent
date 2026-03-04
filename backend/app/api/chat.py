"""Document Q&A chat API.

Provides RAG-based chat over uploaded documents with conversation history
awareness. Files are indexed on-demand before the first query.
"""

import logging
from pathlib import Path
from typing import Any

import litellm
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import CurrentUser
from app.config import get_settings
from app.services.document_parser import ParserFactory
from app.services.embedding_service import EmbeddingService
from app.services.supabase import get_supabase_client

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

CHAT_MODEL = "anthropic/claude-sonnet-4-20250514"
TOP_K_CHUNKS = 6

SYSTEM_PROMPT = """You are a helpful document assistant. Your job is to answer questions about the user's uploaded documents accurately and concisely.

Guidelines:
- Base your answers ONLY on the provided document context below
- When referencing information, mention the source document and page/section (e.g. "According to report.pdf page 3...")
- If the answer cannot be found in the documents, say so clearly
- Be concise but complete
- For follow-up questions, use the conversation history for context"""


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatIndexRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1, max_length=20)


class ChatIndexResponse(BaseModel):
    already_indexed: list[str]
    newly_indexed: list[str]
    failed: list[str]


class ChatAskRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1, max_length=20)
    message: str = Field(min_length=1, max_length=4000)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=20)


class ChatSource(BaseModel):
    file_name: str
    page: int | None = None
    sheet_name: str | None = None
    content: str
    similarity: float


class ChatAskResponse(BaseModel):
    answer: str
    sources: list[ChatSource]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _parse_and_index_file(
    supabase,
    sf: dict[str, Any],
    user_id: str,
    embedding_service: EmbeddingService,
) -> int:
    """Download, parse, and index a single source file. Returns chunk count."""
    file_name = sf.get("file_name", "unknown")
    storage_path = sf.get("storage_path")

    if not storage_path:
        raise ValueError(f"No storage path for file: {file_name}")

    # Download file content
    file_content = supabase.storage.from_(settings.upload_bucket).download(storage_path)

    # Parse into structured document
    file_type = sf.get("file_type", "")
    parsed_doc = ParserFactory.parse_file_to_document(
        file_content=file_content,
        file_extension=file_type,
        file_name=file_name,
        user_id=user_id,
        source_file_id=sf["id"],
    )

    # Cache parsed content if not already done
    if sf.get("parsing_status") != "completed":
        try:
            supabase.table("source_files").update({
                "parsed_content": parsed_doc.raw_text,
                "parsing_status": "completed",
            }).eq("id", sf["id"]).execute()
        except Exception as e:
            logger.warning(f"[CHAT] Failed to cache parsed content for {file_name}: {e}")

    # Index into pgvector
    count = await embedding_service.index_document(parsed_doc)
    logger.info(f"[CHAT] Indexed {count} chunks from {file_name}")
    return count


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/index", response_model=ChatIndexResponse)
@limiter.limit("10/minute")
async def index_files_for_chat(
    request: Request,
    current_user: CurrentUser,
    body: ChatIndexRequest,
):
    """Pre-index uploaded files for chat.

    Downloads, parses, and embeds files that have not yet been indexed.
    Already-indexed files are skipped. Call this before the first chat session.
    """
    supabase = get_supabase_client()

    # Verify files belong to user
    files_result = supabase.table("source_files").select(
        "id, file_name, file_type, storage_path, parsing_status, parsed_content"
    ).in_("id", body.file_ids).eq("user_id", current_user.id).execute()

    found_ids = {sf["id"] for sf in files_result.data}
    for fid in body.file_ids:
        if fid not in found_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {fid}",
            )

    embedding_service = EmbeddingService()
    indexed_ids = await embedding_service.get_indexed_file_ids(current_user.id)

    already_indexed: list[str] = []
    newly_indexed: list[str] = []
    failed: list[str] = []

    for sf in files_result.data:
        fid = sf["id"]
        if fid in indexed_ids:
            already_indexed.append(fid)
            continue

        try:
            await _parse_and_index_file(supabase, sf, current_user.id, embedding_service)
            newly_indexed.append(fid)
        except Exception as e:
            logger.error(f"[CHAT] Failed to index file {sf.get('file_name')}: {e}")
            failed.append(fid)

    logger.info(
        f"[CHAT] User {current_user.id} | Index: "
        f"already={len(already_indexed)}, new={len(newly_indexed)}, failed={len(failed)}"
    )

    return ChatIndexResponse(
        already_indexed=already_indexed,
        newly_indexed=newly_indexed,
        failed=failed,
    )


@router.post("/ask", response_model=ChatAskResponse)
@limiter.limit("20/minute")
async def ask_document_question(
    request: Request,
    current_user: CurrentUser,
    body: ChatAskRequest,
):
    """Answer a question about uploaded documents using RAG.

    Searches indexed document chunks for relevant context, then uses the LLM
    to generate a grounded answer with source citations. Conversation history
    is included so the model can handle follow-up questions.
    """
    supabase = get_supabase_client()

    # Verify files belong to user
    files_result = supabase.table("source_files").select("id").in_(
        "id", body.file_ids
    ).eq("user_id", current_user.id).execute()

    found_ids = {sf["id"] for sf in files_result.data}
    for fid in body.file_ids:
        if fid not in found_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {fid}",
            )

    # Similarity search over indexed chunks
    embedding_service = EmbeddingService()
    raw_sources = await embedding_service.similarity_search(
        query=body.message,
        user_id=current_user.id,
        top_k=TOP_K_CHUNKS,
        source_file_ids=body.file_ids,
    )

    if not raw_sources:
        # Files may not be indexed yet — attempt on-demand indexing
        logger.info(f"[CHAT] No indexed chunks found, attempting on-demand indexing")
        files_full = supabase.table("source_files").select(
            "id, file_name, file_type, storage_path, parsing_status, parsed_content"
        ).in_("id", body.file_ids).eq("user_id", current_user.id).execute()

        for sf in files_full.data:
            try:
                await _parse_and_index_file(supabase, sf, current_user.id, embedding_service)
            except Exception as e:
                logger.warning(f"[CHAT] On-demand index failed for {sf.get('file_name')}: {e}")

        # Re-run search after indexing
        raw_sources = await embedding_service.similarity_search(
            query=body.message,
            user_id=current_user.id,
            top_k=TOP_K_CHUNKS,
            source_file_ids=body.file_ids,
        )

    # Build context block from retrieved chunks
    context_parts: list[str] = []
    sources: list[ChatSource] = []

    for chunk in raw_sources:
        metadata = chunk.get("metadata", {})
        file_name = metadata.get("file_name", "Unknown document")
        page = metadata.get("page_number")
        sheet = metadata.get("sheet_name")
        content = chunk.get("content", "")
        similarity = chunk.get("similarity", 0.0)

        # Format context reference
        ref_parts = [f"[Source: {file_name}"]
        if page:
            ref_parts.append(f"page {page}")
        if sheet:
            ref_parts.append(f"sheet '{sheet}'")
        ref_parts.append("]")
        ref = " ".join(ref_parts[:-1]) + ref_parts[-1] if len(ref_parts) > 2 else ref_parts[0] + ref_parts[-1]

        context_parts.append(f"{ref}\n{content}")
        sources.append(ChatSource(
            file_name=file_name,
            page=page,
            sheet_name=sheet,
            content=content[:300],  # Truncate for response payload
            similarity=round(similarity, 3),
        ))

    context_block = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant document content found."

    # Build message list for LLM (system + history + new user message with context)
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history (interleaved roles)
    for msg in body.conversation_history:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    # Current question with context injected
    user_message_with_context = (
        f"Document Context:\n{context_block}\n\n"
        f"Question: {body.message}"
    )
    messages.append({"role": "user", "content": user_message_with_context})

    # Call LLM
    try:
        response = await litellm.acompletion(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=1500,
            temperature=0.2,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[CHAT] LLM call failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer. Please try again.",
        )

    logger.info(
        f"[CHAT] User {current_user.id} | "
        f"sources={len(sources)}, answer_len={len(answer)}"
    )

    return ChatAskResponse(answer=answer, sources=sources)
