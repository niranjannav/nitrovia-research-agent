-- Migration 004: Finance records table
-- Run in Supabase SQL editor after 003_analytics_tables.sql

CREATE TABLE IF NOT EXISTS finance_records (
  id                   UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  record_date          DATE NOT NULL,
  user_id              UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  upload_id            UUID NOT NULL REFERENCES analytics_uploads(id) ON DELETE CASCADE,

  -- P&L metrics
  revenue              NUMERIC,
  cogs                 NUMERIC,
  gross_profit         NUMERIC,
  gross_profit_pct     NUMERIC,
  other_income         NUMERIC,
  operating_expenses   NUMERIC,
  operating_profit     NUMERIC,
  ebit                 NUMERIC,
  ebitda               NUMERIC,
  net_income           NUMERIC,

  -- Volume metrics
  litres_sold          NUMERIC,
  revenue_per_litre    NUMERIC,
  cost_per_litre       NUMERIC,

  -- Balance sheet
  total_assets         NUMERIC,
  total_liabilities    NUMERIC,
  total_equity         NUMERIC,

  -- Cash flow
  operating_cash_flow  NUMERIC,
  investing_cash_flow  NUMERIC,
  financing_cash_flow  NUMERIC,
  net_cash_flow        NUMERIC,

  created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_finance_records_user_date
  ON finance_records(user_id, record_date);

CREATE INDEX IF NOT EXISTS idx_finance_records_upload
  ON finance_records(upload_id);

-- Enable RLS
ALTER TABLE finance_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access own finance records"
  ON finance_records FOR ALL
  USING (auth.uid() = user_id);
