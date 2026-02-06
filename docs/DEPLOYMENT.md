# Deployment Guide

Step-by-step guide to deploy the Research Report Generator.

## Prerequisites

### Accounts Needed
1. **Supabase** (free tier) - [supabase.com](https://supabase.com)
2. **Railway** (free tier) - [railway.app](https://railway.app)
3. **Cloudflare** (free) - [cloudflare.com](https://cloudflare.com)
4. **Google Cloud** - [console.cloud.google.com](https://console.cloud.google.com)
5. **Anthropic** - [console.anthropic.com](https://console.anthropic.com)
6. **GitHub** - [github.com](https://github.com)

### Local Tools
- Git
- Node.js 18+
- Python 3.11+ (for local testing)

---

## Step 1: Supabase Setup

### 1.1 Create Project
1. Sign up at [supabase.com](https://supabase.com)
2. Create new project
3. Note down:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon key**: Found in Settings > API
   - **service_role key**: Found in Settings > API (keep secret!)

### 1.2 Run Database Migration
1. Go to SQL Editor in Supabase dashboard
2. Copy contents of `docs/supabase-migration.sql`
3. Paste and click "Run"

### 1.3 Configure Auth
1. Settings > Authentication > Providers
2. Enable "Email" provider
3. Optionally enable "Google" OAuth

### 1.4 Create Storage Buckets
1. Go to Storage
2. Create bucket: `uploads` (private)
3. Create bucket: `generated-reports` (private)

### 1.5 Storage Policies
For each bucket, add policies:

**uploads bucket:**
```sql
-- Allow authenticated users to upload to their folder
CREATE POLICY "Users can upload files" ON storage.objects
FOR INSERT WITH CHECK (
    bucket_id = 'uploads' AND
    auth.uid()::text = (storage.foldername(name))[1]
);

-- Allow users to read their own files
CREATE POLICY "Users can read own files" ON storage.objects
FOR SELECT USING (
    bucket_id = 'uploads' AND
    auth.uid()::text = (storage.foldername(name))[1]
);
```

**generated-reports bucket:**
```sql
-- Similar policies for generated-reports bucket
CREATE POLICY "Users can read generated reports" ON storage.objects
FOR SELECT USING (
    bucket_id = 'generated-reports' AND
    auth.uid()::text = (storage.foldername(name))[1]
);
```

---

## Step 2: Google Cloud Setup

### 2.1 Create Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create new project: "Research Report Generator"

### 2.2 Enable Drive API
1. Go to "APIs & Services" > "Library"
2. Search for "Google Drive API"
3. Click "Enable"

### 2.3 Create Service Account
1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name: `report-generator-sa`
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

### 2.4 Create Key
1. Click on the service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON"
5. Download the file

### 2.5 Encode for Environment Variable
```bash
# Linux/Mac
cat service-account.json | base64 -w 0

# Windows PowerShell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("service-account.json"))
```

Save this base64 string for `GOOGLE_SERVICE_ACCOUNT_JSON`.

---

## Step 3: Anthropic Setup

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Go to "API Keys"
3. Create new API key
4. Add billing (pay-as-you-go)
5. Save the key: `sk-ant-...`

---

## Step 4: Deploy Backend (Railway)

### 4.1 Push Code to GitHub
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 4.2 Connect to Railway
1. Sign up at [railway.app](https://railway.app)
2. Click "New Project" > "Deploy from GitHub Repo"
3. Select your repository
4. Set root directory: `/backend`

### 4.3 Configure Environment Variables
In Railway project settings, add:

```
ENVIRONMENT=production
LOG_LEVEL=INFO
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SERVICE_ACCOUNT_JSON=base64-encoded-json
CORS_ORIGINS=https://your-app.pages.dev
UPLOAD_BUCKET=uploads
OUTPUT_BUCKET=generated-reports
MAX_FILE_SIZE_MB=50
```

### 4.4 Configure Settings
1. Settings > Healthcheck Path: `/health`
2. Note your deployment URL: `https://xxxx.railway.app`

---

## Step 5: Deploy Frontend (Cloudflare Pages)

### 5.1 Connect to Cloudflare
1. Sign up at [cloudflare.com](https://cloudflare.com)
2. Go to "Pages"
3. Click "Create a project" > "Connect to Git"
4. Select your repository

### 5.2 Configure Build Settings
- **Framework preset**: Vite
- **Build command**: `npm run build`
- **Build output directory**: `dist`
- **Root directory**: `frontend`

### 5.3 Add Environment Variables
```
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_URL=https://your-api.railway.app
```

### 5.4 Deploy
Click "Save and Deploy"

### 5.5 Custom Domain (Optional)
1. Go to your Pages project > Custom domains
2. Add your domain
3. Follow DNS configuration instructions

---

## Step 6: Post-Deployment Verification

### 6.1 Backend Health Check
```bash
curl https://your-api.railway.app/health
# Should return: {"status":"healthy","version":"1.0.0"}
```

### 6.2 Frontend
1. Visit your Cloudflare Pages URL
2. Should see the login page

### 6.3 Full Flow Test
1. Sign up with a new account
2. Upload a small PDF file
3. Configure and generate a report
4. Verify download works

---

## Troubleshooting

### CORS Errors
- Ensure `CORS_ORIGINS` in Railway includes your frontend URL
- Don't include trailing slash

### Auth Not Working
- Verify Supabase URL and anon key in frontend
- Check Supabase Auth settings

### Storage Upload Fails
- Verify storage buckets exist
- Check storage policies are applied

### Report Generation Fails
- Check Railway logs for errors
- Verify Anthropic API key is valid and has credits
- Check file size limits

---

## Updating the Application

### Code Updates
1. Push changes to GitHub
2. Both Railway and Cloudflare auto-deploy on push

### Environment Variable Changes
1. Update in Railway/Cloudflare settings
2. Trigger redeploy

### Database Changes
1. Write migration SQL
2. Run in Supabase SQL Editor
3. Update backend models if needed
