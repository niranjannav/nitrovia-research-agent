-- Migration: Analytics tables for structured Excel data ingestion
-- Supports Sales, Production, QA, and Finance domains.
-- Uses AI-powered schema inference so any Excel format is supported.
-- Run this in your Supabase SQL Editor.

-- ============================================================
-- Schema mapping table (saved once per Excel format, reused)
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_schema_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    domain TEXT NOT NULL CHECK (domain IN ('sales', 'production', 'qa', 'finance')),
    mapping_name TEXT,                 -- e.g. "SMILK Sales Format v1"
    mapping JSONB NOT NULL,            -- full SchemaMapping JSON object
    confirmed_by_user BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schema_mappings_user_domain
    ON analytics_schema_mappings(user_id, domain);

-- ============================================================
-- Upload tracking table
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    domain TEXT NOT NULL CHECK (domain IN ('sales', 'production', 'qa', 'finance')),
    mapping_id UUID REFERENCES analytics_schema_mappings(id) ON DELETE SET NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    file_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    row_count INT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_uploads_user_domain
    ON analytics_uploads(user_id, domain, created_at DESC);

-- ============================================================
-- Sales records (normalized from Excel via SchemaMapping)
-- ============================================================
CREATE TABLE IF NOT EXISTS sales_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID NOT NULL REFERENCES analytics_uploads(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    record_date DATE NOT NULL,        -- first day of the month this record belongs to
    product_code TEXT,
    product_name TEXT,
    customer_code TEXT,
    customer_name TEXT,
    channel TEXT,                     -- 'Dealers' | 'POS' | 'Firm' | 'HMD' | 'Wholesale' | 'Export'
    region TEXT,
    salesperson TEXT,
    team TEXT,
    quantity_units NUMERIC,
    quantity_litres NUMERIC,
    revenue NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_sales_user_date
    ON sales_records(user_id, record_date);
CREATE INDEX IF NOT EXISTS idx_sales_channel
    ON sales_records(user_id, channel);
CREATE INDEX IF NOT EXISTS idx_sales_product
    ON sales_records(user_id, product_code);
CREATE INDEX IF NOT EXISTS idx_sales_salesperson
    ON sales_records(user_id, salesperson);
CREATE INDEX IF NOT EXISTS idx_sales_upload
    ON sales_records(upload_id);

-- ============================================================
-- Row Level Security
-- ============================================================
ALTER TABLE analytics_schema_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_records ENABLE ROW LEVEL SECURITY;

-- User policies (anon key / frontend access)
CREATE POLICY "Users can view own schema mappings"
    ON analytics_schema_mappings FOR SELECT
    USING (user_id = auth.uid()::text);

CREATE POLICY "Users can view own uploads"
    ON analytics_uploads FOR SELECT
    USING (user_id = auth.uid()::text);

CREATE POLICY "Users can view own sales records"
    ON sales_records FOR SELECT
    USING (user_id = auth.uid()::text);

-- Service role full access (for backend operations using service key)
CREATE POLICY "Service role full access to schema mappings"
    ON analytics_schema_mappings FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to analytics uploads"
    ON analytics_uploads FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to sales records"
    ON sales_records FOR ALL
    USING (true) WITH CHECK (true);
