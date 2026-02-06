# Research Report Generator - Maintenance Guide

This guide helps you maintain and troubleshoot the Research Report Generator application.

## System Overview

- **Frontend**: React application hosted on Cloudflare Pages
- **Backend**: FastAPI (Python) hosted on Railway
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase Storage
- **Auth**: Supabase Auth

## Health Checks

### Daily (Automated)
Set up monitoring with UptimeRobot or similar:
- Monitor: `https://your-api.railway.app/health`
- Expected response: `{"status": "healthy", "version": "1.0.0"}`

### Weekly Manual Check (~5 minutes)
1. **Railway Dashboard**: Check "Deployments" shows "Active"
2. **Railway Metrics**: Memory should be under 512MB
3. **Railway Logs**: No repeated errors
4. **Supabase Dashboard**: Check storage usage

## Common Issues & Solutions

### "Site won't load"
1. Check Railway deployment status
2. Click "Redeploy" if crashed
3. Check Cloudflare Pages deployment

### "Report generation stuck"
1. Check if Anthropic API key is valid
2. Try generating with a smaller file
3. Check Railway logs for errors
4. Database check: Reports may be stuck in "processing" status

### "File upload fails"
1. Verify file is under 50MB
2. Ensure file is PDF, DOCX, XLSX, or PPTX
3. Check Supabase Storage quota (1GB free tier)

### "Google Drive not showing files"
1. Verify folder is shared with service account
2. Service account email: (check Railway environment variables)
3. Check if `GOOGLE_SERVICE_ACCOUNT_JSON` is set correctly

### "Authentication errors"
1. Clear browser cookies/cache
2. Check Supabase Auth dashboard
3. Verify `SUPABASE_URL` and keys are correct

## Restarting Services

### Backend (Railway)
1. Go to [railway.app](https://railway.app), log in
2. Select the project
3. Go to Deployments
4. Click "Redeploy" on latest deployment
5. Wait 2-3 minutes

### Frontend (Cloudflare)
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Navigate to Pages
3. Select the project
4. Trigger a new deployment or check the current one

## Updating API Keys

### Anthropic API Key
1. Get new key from [console.anthropic.com](https://console.anthropic.com)
2. Go to Railway project settings
3. Update `ANTHROPIC_API_KEY` environment variable
4. Redeploy

### Supabase Keys (if needed)
1. Get keys from Supabase dashboard
2. Update in Railway and Cloudflare Pages
3. Redeploy both services

## Database Maintenance

### Cleaning Old Reports
Reports older than 30 days can be deleted to free storage:

```sql
-- Run in Supabase SQL Editor
DELETE FROM reports
WHERE created_at < NOW() - INTERVAL '30 days';
```

### Checking Storage Usage
```sql
SELECT
  (SELECT COUNT(*) FROM reports) as total_reports,
  (SELECT COUNT(*) FROM source_files) as total_files,
  (SELECT pg_size_pretty(pg_database_size(current_database()))) as db_size;
```

## Monthly Tasks (~15 minutes)

1. **Railway Usage**
   - Check hours used (500 hours/month free)
   - Review if upgrade needed

2. **Supabase Storage**
   - Check storage usage (1GB free)
   - Delete old files if needed

3. **Anthropic Usage**
   - Review API costs at console.anthropic.com
   - Typical: ~$15-25 for 100-150 reports

4. **Error Review**
   - Check Railway logs for recurring errors
   - Check Supabase logs

## Costs Breakdown

| Service | Free Tier | Monthly Cost |
|---------|-----------|--------------|
| Railway | 500 hours | $0 (or $5 hobby) |
| Supabase | 500MB DB, 1GB storage | $0 |
| Cloudflare Pages | Unlimited | $0 |
| Anthropic | Pay per use | ~$15-25/100 reports |

## Emergency Contacts

- Developer: [Your contact info]
- Railway Support: https://railway.app/help
- Supabase Support: https://supabase.com/support
- Cloudflare Support: https://support.cloudflare.com

## Environment Variables Reference

### Backend (Railway)
```
ENVIRONMENT=production
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SERVICE_ACCOUNT_JSON=base64-encoded-json
CORS_ORIGINS=https://your-app.pages.dev
UPLOAD_BUCKET=uploads
OUTPUT_BUCKET=generated-reports
```

### Frontend (Cloudflare Pages)
```
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_URL=https://your-api.railway.app
```

## Troubleshooting Logs

### Check Railway Logs
1. Go to Railway dashboard
2. Select service
3. Click "Logs" tab
4. Look for ERROR level messages

### Common Error Patterns

**"Invalid token"**
- Session expired, user needs to re-login

**"File too large"**
- File exceeds 50MB limit

**"LLM returned invalid JSON"**
- Anthropic API issue, retry generation

**"Failed to parse document"**
- Corrupted or password-protected file

## Updating the Application

### Minor Updates
1. Push changes to GitHub
2. Railway and Cloudflare auto-deploy

### Major Updates
1. Test locally with docker-compose
2. Push to staging branch first (if configured)
3. Verify staging works
4. Merge to main for production deploy

## Backup Procedures

### Database Backup
Supabase provides automatic daily backups on paid plans.
For free tier, manually export:
1. Supabase Dashboard > SQL Editor
2. Run: `pg_dump` equivalent export

### Code Backup
- GitHub repository serves as code backup
- Ensure all environment variables are documented (not committed)
