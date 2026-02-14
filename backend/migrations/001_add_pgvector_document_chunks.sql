-- Migration: Add pgvector support for document chunk storage and similarity search
-- Run this in your Supabase SQL Editor or via migration tool

-- Enable pgvector extension (Supabase has it pre-installed)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the document_chunks table for storing embedded document chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_file_id UUID REFERENCES source_files(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user-scoped queries (ensures document isolation between users)
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_id
    ON document_chunks(user_id);

-- Index for source file lookups
CREATE INDEX IF NOT EXISTS idx_document_chunks_source_file_id
    ON document_chunks(source_file_id);

-- Vector similarity search index using IVFFlat
-- Note: This index requires at least some data to be present.
-- For initial setup with fewer than 1000 rows, you may skip this
-- and add it later when you have more data.
-- CREATE INDEX idx_document_chunks_embedding
--     ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- For small datasets, use HNSW index instead (works with any number of rows)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- RPC function for similarity search with user isolation
-- This is called by the EmbeddingService.similarity_search method
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    filter_user_id TEXT DEFAULT NULL,
    filter_source_file_ids UUID[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    source_file_id UUID,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.content,
        dc.metadata,
        dc.source_file_id,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE
        (filter_user_id IS NULL OR dc.user_id = filter_user_id)
        AND (filter_source_file_ids IS NULL OR dc.source_file_id = ANY(filter_source_file_ids))
        AND dc.embedding IS NOT NULL
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Enable Row Level Security for document_chunks
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- RLS policy: Users can only see their own document chunks
CREATE POLICY "Users can view own document chunks"
    ON document_chunks FOR SELECT
    USING (user_id = auth.uid()::text);

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role full access to document chunks"
    ON document_chunks FOR ALL
    USING (true)
    WITH CHECK (true);
