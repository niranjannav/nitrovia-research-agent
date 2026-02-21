-- ============================================
-- MIGRATION 002: User Quotas & Roles
-- Run this in Supabase SQL Editor
-- ============================================

-- Add role and quota columns to users table
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user',
  ADD COLUMN IF NOT EXISTS monthly_report_limit INTEGER DEFAULT 3,
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- Add index for role lookups
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Add index for active user filtering
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Grant service role full access to new columns (already covered by existing RLS policies)
-- No new RLS policies needed since users table already has "Users can view own profile"

-- ============================================
-- HELPER: Count user's reports this month
-- ============================================
CREATE OR REPLACE FUNCTION count_user_reports_this_month(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER
        FROM reports
        WHERE created_by = p_user_id
          AND status != 'failed'
          AND created_at >= date_trunc('month', NOW())
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Set yourself as admin (replace with your user ID)
-- ============================================
-- UPDATE users SET role = 'admin', monthly_report_limit = -1 WHERE email = 'your@email.com';
