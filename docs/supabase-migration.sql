-- ============================================
-- RESEARCH REPORT GENERATOR - DATABASE SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- REPORTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,

    -- Report Configuration
    title VARCHAR(500),
    custom_instructions TEXT,
    detail_level VARCHAR(20) NOT NULL,
    output_formats TEXT[] NOT NULL,
    slide_count_min INTEGER DEFAULT 10,
    slide_count_max INTEGER DEFAULT 15,

    -- Status Tracking
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    error_message TEXT,

    -- Source Files (JSON array)
    source_files JSONB NOT NULL DEFAULT '[]',

    -- Generated Content (JSON)
    generated_content JSONB,

    -- Output Files
    output_files JSONB DEFAULT '[]',

    -- Metrics
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    generation_time_seconds INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- SOURCE FILES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS source_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- File Info
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER,
    source VARCHAR(50) NOT NULL,

    -- Storage
    storage_path TEXT,
    google_drive_id TEXT,

    -- Parsing Results
    parsed_content TEXT,
    parsing_status VARCHAR(50) DEFAULT 'pending',
    parsing_error TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- GENERATION LOGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS generation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,

    step VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT,
    metadata JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(created_by);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_files_report ON source_files(report_id);
CREATE INDEX IF NOT EXISTS idx_source_files_user ON source_files(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_logs_report ON generation_logs(report_id);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_logs ENABLE ROW LEVEL SECURITY;

-- Users can see and update their own record
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (id = auth.uid());

-- Users can see their own reports
CREATE POLICY "Users can view own reports" ON reports
    FOR SELECT USING (created_by = auth.uid());

CREATE POLICY "Users can insert own reports" ON reports
    FOR INSERT WITH CHECK (created_by = auth.uid());

CREATE POLICY "Users can update own reports" ON reports
    FOR UPDATE USING (created_by = auth.uid());

CREATE POLICY "Users can delete own reports" ON reports
    FOR DELETE USING (created_by = auth.uid());

-- Users can see their own files
CREATE POLICY "Users can view own files" ON source_files
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert own files" ON source_files
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own files" ON source_files
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can delete own files" ON source_files
    FOR DELETE USING (user_id = auth.uid());

-- Users can see logs for their reports
CREATE POLICY "Users can view own report logs" ON generation_logs
    FOR SELECT USING (
        report_id IN (SELECT id FROM reports WHERE created_by = auth.uid())
    );

-- ============================================
-- FUNCTION: Auto-update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to users table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- FUNCTION: Create user record on signup
-- ============================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name'
    );
    RETURN NEW;
END;
$$ language 'plpgsql' SECURITY DEFINER;

-- Trigger on auth.users insert
CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- ============================================
-- STORAGE BUCKETS (run separately in Storage settings)
-- ============================================
-- Create these buckets manually in Supabase Storage:
-- 1. "uploads" - Private bucket for uploaded files
-- 2. "generated-reports" - Private bucket for generated outputs

-- Storage policies (apply via Supabase dashboard):
-- Users can upload to their own folder: uploads/{user_id}/*
-- Users can download from their own folder

COMMENT ON TABLE users IS 'User profiles linked to Supabase Auth';
COMMENT ON TABLE reports IS 'Generated report metadata and results';
COMMENT ON TABLE source_files IS 'Uploaded source documents';
COMMENT ON TABLE generation_logs IS 'Report generation step logs for debugging';
