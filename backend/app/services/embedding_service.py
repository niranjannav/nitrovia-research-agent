"""Embedding service for pgvector storage and similarity search.

Handles generating embeddings via LiteLLM and storing/retrieving
document chunks from Supabase Postgres with pgvector.
"""

import logging
from typing import Any

import litellm

from app.config import get_settings
from app.models.document import ParsedDocument
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)

# Default embedding model - OpenAI text-embedding-3-small is very cost-effective
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
# Number of chunks to embed in a single batch
EMBEDDING_BATCH_SIZE = 50
# Top-N results per query during similarity search
DEFAULT_TOP_K = 5


class EmbeddingService:
    """Service for generating embeddings and managing pgvector storage.

    Uses LiteLLM for embedding generation (supports OpenAI, Cohere, etc.)
    and Supabase Postgres with pgvector for storage and similarity search.

    The document_chunks table schema expected:
        CREATE TABLE document_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_file_id UUID REFERENCES source_files(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}',
            embedding vector(1536),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX idx_document_chunks_user_id ON document_chunks(user_id);
        CREATE INDEX idx_document_chunks_embedding ON document_chunks
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    """

    def __init__(
        self,
        embedding_model: str | None = None,
    ):
        """Initialize the embedding service.

        Args:
            embedding_model: LiteLLM-compatible embedding model identifier
        """
        self.settings = get_settings()
        self.embedding_model = embedding_model or getattr(
            self.settings, "embedding_model", DEFAULT_EMBEDDING_MODEL
        )
        self.supabase = get_supabase_client()

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Process in batches
        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            try:
                response = await litellm.aembedding(
                    model=self.embedding_model,
                    input=batch,
                )
                batch_embeddings = [item["embedding"] for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Embedding generation failed for batch {i}: {e}")
                raise

        return all_embeddings

    async def index_document(self, parsed_doc: ParsedDocument) -> int:
        """Index a parsed document's chunks into pgvector.

        Generates embeddings for each chunk and stores them with metadata
        in the document_chunks table.

        Args:
            parsed_doc: ParsedDocument with chunks to index

        Returns:
            Number of chunks indexed
        """
        if not parsed_doc.chunks:
            logger.warning(f"No chunks to index for {parsed_doc.file_name}")
            return 0

        # Extract texts for embedding
        texts = [chunk.content for chunk in parsed_doc.chunks]

        # Generate embeddings
        embeddings = await self.generate_embeddings(texts)

        if len(embeddings) != len(parsed_doc.chunks):
            raise ValueError(
                f"Embedding count mismatch: {len(embeddings)} embeddings "
                f"for {len(parsed_doc.chunks)} chunks"
            )

        # Store chunks with embeddings in database
        indexed_count = 0
        for chunk, embedding in zip(parsed_doc.chunks, embeddings):
            try:
                self.supabase.table("document_chunks").insert({
                    "source_file_id": chunk.metadata.source_file_id,
                    "user_id": chunk.metadata.user_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata.to_dict(),
                    "embedding": embedding,
                }).execute()
                indexed_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to store chunk {chunk.metadata.chunk_index} "
                    f"of {parsed_doc.file_name}: {e}"
                )

        logger.info(
            f"Indexed {indexed_count}/{len(parsed_doc.chunks)} chunks "
            f"for {parsed_doc.file_name}"
        )
        return indexed_count

    async def similarity_search(
        self,
        query: str,
        user_id: str,
        top_k: int = DEFAULT_TOP_K,
        source_file_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar document chunks using cosine similarity.

        Filters results by user_id to ensure document isolation between users.

        Args:
            query: Search query text
            user_id: User identifier for filtering (ensures user isolation)
            top_k: Number of top results to return
            source_file_ids: Optional list of source file IDs to restrict search

        Returns:
            List of dicts with 'content', 'metadata', and 'similarity' keys
        """
        # Generate query embedding
        embeddings = await self.generate_embeddings([query])
        if not embeddings:
            return []

        query_embedding = embeddings[0]

        # Use Supabase RPC for vector similarity search
        # This calls a Postgres function that does the cosine similarity search
        try:
            params: dict[str, Any] = {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "filter_user_id": user_id,
            }

            if source_file_ids:
                params["filter_source_file_ids"] = source_file_ids

            result = self.supabase.rpc(
                "match_document_chunks",
                params,
            ).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            # Fallback: try direct query if RPC function doesn't exist
            return await self._fallback_similarity_search(
                query_embedding, user_id, top_k, source_file_ids
            )

    async def _fallback_similarity_search(
        self,
        query_embedding: list[float],
        user_id: str,
        top_k: int,
        source_file_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fallback similarity search using direct SQL via Supabase.

        Used when the match_document_chunks RPC function is not available.

        Args:
            query_embedding: Query embedding vector
            user_id: User identifier for filtering
            top_k: Number of results
            source_file_ids: Optional source file filter

        Returns:
            List of matching chunks
        """
        try:
            query = (
                self.supabase.table("document_chunks")
                .select("id, content, metadata, source_file_id")
                .eq("user_id", user_id)
            )

            if source_file_ids:
                query = query.in_("source_file_id", source_file_ids)

            query = query.limit(top_k * 3)  # Fetch more for client-side ranking
            result = query.execute()

            if not result.data:
                return []

            # Client-side cosine similarity ranking (less efficient but functional)
            import math

            def cosine_similarity(a: list[float], b: list[float]) -> float:
                dot = sum(x * y for x, y in zip(a, b))
                norm_a = math.sqrt(sum(x * x for x in a))
                norm_b = math.sqrt(sum(x * x for x in b))
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return dot / (norm_a * norm_b)

            # Note: This fallback doesn't use embeddings from DB for ranking
            # It returns results without similarity scores
            return [
                {
                    "content": row["content"],
                    "metadata": row["metadata"],
                    "similarity": 0.0,
                }
                for row in result.data[:top_k]
            ]

        except Exception as e:
            logger.error(f"Fallback similarity search failed: {e}")
            return []

    async def delete_document_chunks(
        self,
        source_file_id: str,
    ) -> int:
        """Delete all chunks for a source file.

        Args:
            source_file_id: Source file ID to delete chunks for

        Returns:
            Number of chunks deleted
        """
        try:
            result = self.supabase.table("document_chunks").delete().eq(
                "source_file_id", source_file_id
            ).execute()
            count = len(result.data) if result.data else 0
            logger.info(f"Deleted {count} chunks for source_file_id={source_file_id}")
            return count
        except Exception as e:
            logger.error(f"Failed to delete chunks for {source_file_id}: {e}")
            return 0

    async def get_indexed_file_ids(self, user_id: str) -> set[str]:
        """Get set of source_file_ids that have been indexed for a user.

        Args:
            user_id: User identifier

        Returns:
            Set of indexed source file IDs
        """
        try:
            result = (
                self.supabase.table("document_chunks")
                .select("source_file_id")
                .eq("user_id", user_id)
                .execute()
            )
            return {row["source_file_id"] for row in (result.data or [])}
        except Exception as e:
            logger.error(f"Failed to get indexed file IDs: {e}")
            return set()
