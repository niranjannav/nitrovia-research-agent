# Research Report Generator - Complete Project Specification

## Project Overview

**Client**: Small business (technologically nascent)
**Purpose**: Automated research report and presentation generation from uploaded documents
**Handoff**: Self-sustainable system with maintenance documentation

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Technology Stack](#technology-stack)
3. [Directory Structure](#directory-structure)
4. [Database Schema](#database-schema)
5. [API Specification](#api-specification)
6. [Frontend Components](#frontend-components)
7. [Document Processing Pipeline](#document-processing-pipeline)
8. [Report Generation Logic](#report-generation-logic)
9. [Presentation Generation Logic](#presentation-generation-logic)
10. [Configuration & Environment](#configuration--environment)
11. [Deployment Guide](#deployment-guide)
12. [Maintenance Runbook](#maintenance-runbook)
13. [Cost Projections](#cost-projections)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USERS                                       │
│                    (Client + Team Members)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     CLOUDFLARE PAGES (Frontend)                          │
│                        react-report-generator                            │
│                                                                          │
│  • Authentication UI (Google OAuth / Email-Password)                     │
│  • File Upload & Google Drive Picker                                     │
│  • Report Configuration Form                                             │
│  • Generation Progress & Download Interface                              │
│  • Settings (API Keys, Brand Config)                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        RAILWAY (Backend)                                 │
│                      fastapi-report-service                              │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐ │
│  │  Auth Routes   │  │  Report Routes │  │  Settings Routes           │ │
│  │  /auth/*       │  │  /reports/*    │  │  /settings/*               │ │
│  └────────────────┘  └────────────────┘  └────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    PROCESSING PIPELINE                            │   │
│  │                                                                   │   │
│  │  Ingestion → Parsing → Context Prep → LLM Gen → Rendering        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
           │                    │                         │
           ▼                    ▼                         ▼
┌──────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│   SUPABASE       │  │  GOOGLE DRIVE   │  │    EXTERNAL APIS            │
│                  │  │                 │  │                             │
│  • Auth          │  │  Service Acct   │  │  • Anthropic (Claude)       │
│  • PostgreSQL    │  │  Shared Folder  │  │  • Serper (Web Search)      │
│  • Storage       │  │                 │  │                             │
└──────────────────┘  └─────────────────┘  └─────────────────────────────┘
```

### Design Principles

1. **Stateless Backend**: No session state on server; all state in DB or client
2. **Async Processing**: Report generation runs async with polling for status
3. **Fail-Safe Defaults**: If any optional service fails, gracefully degrade
4. **Observable**: Comprehensive logging for debugging without access
5. **Self-Healing**: Auto-restart on crash, retry failed API calls

---

## Technology Stack

### Frontend
| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | React 18 + Vite | Fast builds, you know it |
| Styling | Tailwind CSS | Consistent with Nitrovia site |
| State | Zustand | Simpler than Redux, sufficient |
| HTTP | Axios | Cleaner API than fetch |
| Auth | Supabase JS Client | Handles OAuth flow |
| File Upload | react-dropzone | Polished UX |
| Google Picker | @react-google-drive-picker | Drive integration |

### Backend
| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | FastAPI | Async, typed, auto-docs |
| Server | Uvicorn | ASGI, production ready |
| Auth | Supabase Python | Verify JWTs |
| Database | asyncpg + SQLAlchemy | Async Postgres |
| Task Queue | None (async endpoints) | Simplicity; revisit if needed |
| PDF Parse | PyMuPDF (fitz) | Fast, reliable |
| DOCX Parse | python-docx | Standard |
| XLSX Parse | openpyxl | Standard |
| PPTX Parse | python-pptx | Standard |
| PDF Generate | WeasyPrint | HTML→PDF, good styling |
| DOCX Generate | python-docx | Standard |
| PPTX Generate | python-pptx | Standard |
| LLM | anthropic SDK | Claude Sonnet |
| Web Search | httpx + Serper API | Cheap, simple |

### Infrastructure
| Component | Service | Cost |
|-----------|---------|------|
| Frontend Hosting | Cloudflare Pages | $0 |
| Backend Hosting | Railway | ~$5-10/month |
| Database | Supabase (Free tier) | $0 |
| Auth | Supabase Auth | $0 |
| File Storage | Supabase Storage | $0 (under 1GB) |
| LLM API | Anthropic | Client pays directly |
| Web Search | Serper | $0 (free tier) |

**Total Infrastructure**: ~$5-10/month

---

## Directory Structure

```
research-report-generator/
│
├── README.md                     # Project overview & quick start
├── PROJECT_SPEC.md              # This document
├── MAINTENANCE.md               # Runbook for client handoff
├── docker-compose.yml           # Local development setup
├── .env.example                 # Environment template
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings & env loading
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py          # Dependency injection
│   │   │   ├── auth.py          # Auth routes
│   │   │   ├── reports.py       # Report generation routes
│   │   │   ├── files.py         # File upload routes
│   │   │   ├── settings.py      # User settings routes
│   │   │   └── health.py        # Health check endpoint
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── supabase.py      # Supabase client wrapper
│   │   │   ├── google_drive.py  # Drive API integration
│   │   │   ├── document_parser.py    # Multi-format parsing
│   │   │   ├── context_builder.py    # Prepare LLM context
│   │   │   ├── llm_service.py        # Claude API wrapper
│   │   │   ├── web_search.py         # Serper integration
│   │   │   ├── report_generator.py   # Orchestrates generation
│   │   │   ├── pdf_renderer.py       # JSON → PDF
│   │   │   ├── docx_renderer.py      # JSON → DOCX
│   │   │   └── pptx_renderer.py      # JSON → PPTX
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database.py      # SQLAlchemy models
│   │   │   └── schemas.py       # Pydantic schemas
│   │   │
│   │   ├── templates/
│   │   │   ├── report_base.html      # PDF template
│   │   │   ├── report_detailed.html  # Detailed PDF template
│   │   │   └── styles.css            # PDF styling
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logging.py       # Structured logging
│   │       ├── errors.py        # Custom exceptions
│   │       └── helpers.py       # Misc utilities
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_document_parser.py
│       ├── test_report_generator.py
│       └── test_api.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   │
│   ├── public/
│   │   ├── favicon.ico
│   │   └── logo.svg
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── vite-env.d.ts
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Header.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   └── Layout.tsx
│       │   │
│       │   ├── auth/
│       │   │   ├── LoginForm.tsx
│       │   │   ├── SignupForm.tsx
│       │   │   └── AuthGuard.tsx
│       │   │
│       │   ├── files/
│       │   │   ├── FileUploader.tsx
│       │   │   ├── GoogleDrivePicker.tsx
│       │   │   ├── FileList.tsx
│       │   │   └── FilePreview.tsx
│       │   │
│       │   ├── reports/
│       │   │   ├── ReportConfigForm.tsx
│       │   │   ├── DetailLevelSelector.tsx
│       │   │   ├── OutputFormatSelector.tsx
│       │   │   ├── SlideRangeInput.tsx
│       │   │   ├── WebSearchToggle.tsx
│       │   │   ├── CustomInstructionInput.tsx
│       │   │   ├── GenerationProgress.tsx
│       │   │   ├── ReportHistory.tsx
│       │   │   └── DownloadCard.tsx
│       │   │
│       │   ├── settings/
│       │   │   ├── ApiKeySettings.tsx
│       │   │   ├── BrandSettings.tsx
│       │   │   └── TeamSettings.tsx
│       │   │
│       │   └── common/
│       │       ├── Button.tsx
│       │       ├── Input.tsx
│       │       ├── Select.tsx
│       │       ├── Toggle.tsx
│       │       ├── Card.tsx
│       │       ├── Modal.tsx
│       │       ├── Spinner.tsx
│       │       └── Toast.tsx
│       │
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── DashboardPage.tsx
│       │   ├── NewReportPage.tsx
│       │   ├── ReportHistoryPage.tsx
│       │   └── SettingsPage.tsx
│       │
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   ├── useReports.ts
│       │   ├── useFiles.ts
│       │   └── useSettings.ts
│       │
│       ├── stores/
│       │   ├── authStore.ts
│       │   ├── reportStore.ts
│       │   └── settingsStore.ts
│       │
│       ├── services/
│       │   ├── api.ts            # Axios instance
│       │   ├── authService.ts
│       │   ├── reportService.ts
│       │   ├── fileService.ts
│       │   └── settingsService.ts
│       │
│       ├── types/
│       │   ├── auth.ts
│       │   ├── report.ts
│       │   ├── file.ts
│       │   └── settings.ts
│       │
│       └── utils/
│           ├── constants.ts
│           ├── formatters.ts
│           └── validators.ts
│
└── docs/
    ├── API.md                   # API documentation
    ├── DEPLOYMENT.md            # Step-by-step deployment
    └── TROUBLESHOOTING.md       # Common issues & fixes
```

---

## Database Schema

### Supabase PostgreSQL

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ORGANIZATIONS (for multi-tenant support)
-- ============================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    
    -- Branding
    logo_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#2563EB',  -- Hex color
    secondary_color VARCHAR(7) DEFAULT '#1E40AF',
    
    -- API Keys (encrypted at rest by Supabase)
    anthropic_api_key TEXT,
    serper_api_key TEXT,
    
    -- Google Drive Integration
    google_drive_folder_id TEXT,  -- Shared folder ID
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- USERS
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member',  -- 'admin', 'member'
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- REPORT TEMPLATES (pre-built styling options)
-- ============================================
CREATE TABLE report_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    template_type VARCHAR(20) NOT NULL,  -- 'pdf', 'docx', 'pptx'
    
    -- Template configuration (JSON)
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Whether this is a system template or user-created
    is_system BOOLEAN DEFAULT FALSE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- REPORTS
-- ============================================
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    
    -- Report Configuration
    title VARCHAR(500),
    custom_instructions TEXT,
    detail_level VARCHAR(20) NOT NULL,  -- 'executive', 'standard', 'comprehensive'
    output_formats TEXT[] NOT NULL,      -- ['pdf', 'docx', 'pptx']
    include_web_search BOOLEAN DEFAULT FALSE,
    slide_count_min INTEGER DEFAULT 10,
    slide_count_max INTEGER DEFAULT 15,
    
    -- Status Tracking
    status VARCHAR(50) DEFAULT 'pending',  
    -- 'pending', 'processing', 'parsing', 'generating', 'rendering', 'completed', 'failed'
    progress INTEGER DEFAULT 0,            -- 0-100
    error_message TEXT,
    
    -- Source Files (JSON array)
    source_files JSONB NOT NULL DEFAULT '[]',
    -- [{ "name": "file.pdf", "source": "upload|drive", "path": "...", "size": 1234 }]
    
    -- Generated Content (stored as JSON for flexibility)
    generated_content JSONB,
    -- Full structured output from LLM
    
    -- Output Files
    output_files JSONB DEFAULT '[]',
    -- [{ "format": "pdf", "storage_path": "...", "download_url": "...", "expires_at": "..." }]
    
    -- Metrics
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    generation_time_seconds INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- SOURCE FILES (detailed tracking)
-- ============================================
CREATE TABLE source_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- File Info
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- 'pdf', 'docx', 'xlsx', 'pptx'
    file_size INTEGER,               -- bytes
    source VARCHAR(50) NOT NULL,     -- 'upload', 'google_drive'
    
    -- Storage
    storage_path TEXT,               -- Supabase storage path
    google_drive_id TEXT,            -- If from Drive
    
    -- Parsing Results
    parsed_content TEXT,             -- Extracted text
    parsing_status VARCHAR(50) DEFAULT 'pending',
    parsing_error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- GENERATION LOGS (for debugging)
-- ============================================
CREATE TABLE generation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    
    step VARCHAR(100) NOT NULL,      -- 'parsing', 'context_build', 'llm_call', 'rendering'
    status VARCHAR(50) NOT NULL,     -- 'started', 'completed', 'failed'
    message TEXT,
    metadata JSONB,                  -- Any additional data
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX idx_reports_organization ON reports(organization_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_source_files_report ON source_files(report_id);
CREATE INDEX idx_generation_logs_report ON generation_logs(report_id);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_logs ENABLE ROW LEVEL SECURITY;

-- Users can only see their organization's data
CREATE POLICY "Users see own org" ON organizations
    FOR ALL USING (
        id IN (SELECT organization_id FROM users WHERE id = auth.uid())
    );

CREATE POLICY "Users see own org reports" ON reports
    FOR ALL USING (
        organization_id IN (SELECT organization_id FROM users WHERE id = auth.uid())
    );

CREATE POLICY "Users see own org files" ON source_files
    FOR ALL USING (
        organization_id IN (SELECT organization_id FROM users WHERE id = auth.uid())
    );

-- ============================================
-- SEED DATA: Default Templates
-- ============================================
INSERT INTO report_templates (name, description, template_type, config, is_system) VALUES
(
    'Clean Professional',
    'Minimalist design with clear typography',
    'pdf',
    '{"font_family": "Inter", "heading_color": "#1a1a1a", "accent_color": "#2563EB"}',
    TRUE
),
(
    'Corporate Blue',
    'Traditional corporate style with blue accents',
    'pdf',
    '{"font_family": "Georgia", "heading_color": "#1E3A5F", "accent_color": "#3B82F6"}',
    TRUE
),
(
    'Modern Slides',
    'Clean presentation with gradient backgrounds',
    'pptx',
    '{"theme": "modern", "background_style": "gradient", "title_position": "left"}',
    TRUE
),
(
    'Minimal Slides',
    'Text-focused with plenty of white space',
    'pptx',
    '{"theme": "minimal", "background_style": "solid", "title_position": "center"}',
    TRUE
);
```

---

## API Specification

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://api.reportgen.nitrovialabs.com` (or Railway URL)

### Authentication
All endpoints except `/health` and `/auth/*` require Bearer token.

```
Authorization: Bearer <supabase_access_token>
```

### Endpoints

#### Health Check
```
GET /health
Response: { "status": "healthy", "version": "1.0.0" }
```

#### Authentication
```
POST /auth/signup
Body: { "email": "...", "password": "...", "full_name": "..." }
Response: { "user": {...}, "session": {...} }

POST /auth/login
Body: { "email": "...", "password": "..." }
Response: { "user": {...}, "session": {...} }

POST /auth/logout
Response: { "success": true }

GET /auth/me
Response: { "user": {...}, "organization": {...} }
```

#### Files
```
POST /files/upload
Content-Type: multipart/form-data
Body: file (binary), file_type (string)
Response: { "file_id": "...", "file_name": "...", "storage_path": "..." }

GET /files/drive/list
Query: folder_id (optional)
Response: { "files": [{ "id": "...", "name": "...", "mimeType": "..." }] }

POST /files/drive/select
Body: { "file_ids": ["...", "..."] }
Response: { "files": [{ "file_id": "...", "file_name": "...", "status": "queued" }] }
```

#### Reports
```
POST /reports/generate
Body: {
    "title": "Q4 Market Analysis",
    "custom_instructions": "Focus on competitor pricing strategies...",
    "detail_level": "standard",           // "executive" | "standard" | "comprehensive"
    "output_formats": ["pdf", "pptx"],    // ["pdf", "docx", "pptx"]
    "include_web_search": true,
    "slide_count": { "min": 10, "max": 15 },
    "source_file_ids": ["uuid-1", "uuid-2"]
}
Response: {
    "report_id": "uuid",
    "status": "processing",
    "estimated_time_seconds": 120
}

GET /reports/{report_id}
Response: {
    "id": "uuid",
    "title": "...",
    "status": "completed",
    "progress": 100,
    "output_files": [
        { "format": "pdf", "download_url": "...", "expires_at": "..." },
        { "format": "pptx", "download_url": "...", "expires_at": "..." }
    ],
    "metrics": {
        "total_input_tokens": 15000,
        "total_output_tokens": 4000,
        "generation_time_seconds": 95
    }
}

GET /reports/{report_id}/status
Response: {
    "status": "generating",
    "progress": 65,
    "current_step": "Generating presentation slides..."
}

GET /reports
Query: page (default 1), limit (default 20), status (optional)
Response: {
    "reports": [...],
    "total": 150,
    "page": 1,
    "pages": 8
}

DELETE /reports/{report_id}
Response: { "success": true }
```

#### Settings
```
GET /settings/organization
Response: {
    "name": "Acme Corp",
    "logo_url": "...",
    "primary_color": "#2563EB",
    "has_anthropic_key": true,
    "has_serper_key": false,
    "google_drive_connected": true
}

PATCH /settings/organization
Body: {
    "name": "...",
    "primary_color": "...",
    "anthropic_api_key": "..."  // Only sent when updating
}
Response: { "success": true }

POST /settings/organization/logo
Content-Type: multipart/form-data
Body: file (image)
Response: { "logo_url": "..." }

POST /settings/google-drive/connect
Body: { "folder_id": "..." }
Response: { "success": true, "folder_name": "..." }
```

---

## Frontend Components

### Page Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      App Router                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  /login ──────────────▶ LoginPage                           │
│                            │                                 │
│                            ▼                                 │
│  / ───────────────────▶ DashboardPage (AuthGuard)           │
│                            │                                 │
│                            ├── Quick Stats                   │
│                            ├── Recent Reports                │
│                            └── Quick Actions                 │
│                                                              │
│  /reports/new ────────▶ NewReportPage                       │
│                            │                                 │
│                            ├── FileUploader                  │
│                            ├── GoogleDrivePicker             │
│                            ├── ReportConfigForm              │
│                            │     ├── CustomInstructionInput  │
│                            │     ├── DetailLevelSelector     │
│                            │     ├── OutputFormatSelector    │
│                            │     ├── SlideRangeInput         │
│                            │     └── WebSearchToggle         │
│                            └── GenerationProgress            │
│                                                              │
│  /reports ────────────▶ ReportHistoryPage                   │
│                            │                                 │
│                            └── ReportHistory                 │
│                                  └── DownloadCard (per item) │
│                                                              │
│  /settings ───────────▶ SettingsPage                        │
│                            │                                 │
│                            ├── ApiKeySettings                │
│                            ├── BrandSettings                 │
│                            └── TeamSettings                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Component Specifications

#### ReportConfigForm
```typescript
interface ReportConfig {
  title: string;
  customInstructions: string;
  detailLevel: 'executive' | 'standard' | 'comprehensive';
  outputFormats: ('pdf' | 'docx' | 'pptx')[];
  includeWebSearch: boolean;
  slideCount: {
    min: number;  // 5-20
    max: number;  // 5-20, >= min
  };
  sourceFileIds: string[];
}
```

#### DetailLevelSelector
Visual toggle with descriptions:
- **Executive** (1-2 pages): High-level summary for quick review
- **Standard** (3-5 pages): Balanced detail with key findings
- **Comprehensive** (5-10 pages): In-depth analysis with full context

#### GenerationProgress
Real-time polling (every 2 seconds) showing:
- Progress bar (0-100%)
- Current step description
- Estimated time remaining
- Cancel button (if possible)

---

## Document Processing Pipeline

### Parser Factory Pattern

```python
# backend/app/services/document_parser.py

from abc import ABC, abstractmethod
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

class DocumentParser(ABC):
    @abstractmethod
    async def parse(self, file_path: Path) -> str:
        """Extract text content from document."""
        pass
    
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        pass

class PDFParser(DocumentParser):
    async def parse(self, file_path: Path) -> str:
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        return "\n\n".join(text_parts)
    
    def supported_extensions(self) -> list[str]:
        return ['.pdf']

class DOCXParser(DocumentParser):
    async def parse(self, file_path: Path) -> str:
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    
    def supported_extensions(self) -> list[str]:
        return ['.docx', '.doc']

class XLSXParser(DocumentParser):
    async def parse(self, file_path: Path) -> str:
        wb = load_workbook(file_path, data_only=True)
        text_parts = []
        for sheet in wb.worksheets:
            text_parts.append(f"## Sheet: {sheet.title}\n")
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                if row_text.strip(" |"):
                    text_parts.append(row_text)
        return "\n".join(text_parts)
    
    def supported_extensions(self) -> list[str]:
        return ['.xlsx', '.xls']

class PPTXParser(DocumentParser):
    async def parse(self, file_path: Path) -> str:
        prs = Presentation(file_path)
        text_parts = []
        for i, slide in enumerate(prs.slides, 1):
            slide_text = [f"## Slide {i}"]
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)
            text_parts.append("\n".join(slide_text))
        return "\n\n".join(text_parts)
    
    def supported_extensions(self) -> list[str]:
        return ['.pptx', '.ppt']

class ParserFactory:
    _parsers: dict[str, DocumentParser] = {}
    
    @classmethod
    def register(cls, parser: DocumentParser):
        for ext in parser.supported_extensions():
            cls._parsers[ext.lower()] = parser
    
    @classmethod
    def get_parser(cls, file_path: Path) -> DocumentParser:
        ext = file_path.suffix.lower()
        if ext not in cls._parsers:
            raise ValueError(f"Unsupported file type: {ext}")
        return cls._parsers[ext]

# Register parsers on import
ParserFactory.register(PDFParser())
ParserFactory.register(DOCXParser())
ParserFactory.register(XLSXParser())
ParserFactory.register(PPTXParser())
```

### Context Builder

```python
# backend/app/services/context_builder.py

from dataclasses import dataclass
from anthropic import Anthropic

@dataclass
class DocumentContext:
    file_name: str
    content: str
    token_count: int

@dataclass
class PreparedContext:
    documents: list[DocumentContext]
    total_tokens: int
    was_summarized: bool
    web_search_results: str | None

class ContextBuilder:
    MAX_CONTEXT_TOKENS = 150_000  # Leave room for output
    SUMMARIZE_THRESHOLD = 100_000
    
    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client
    
    async def prepare(
        self,
        documents: list[tuple[str, str]],  # (filename, content)
        include_web_search: bool = False,
        search_query: str | None = None
    ) -> PreparedContext:
        # Count tokens for each document
        doc_contexts = []
        total_tokens = 0
        
        for filename, content in documents:
            tokens = self._count_tokens(content)
            doc_contexts.append(DocumentContext(
                file_name=filename,
                content=content,
                token_count=tokens
            ))
            total_tokens += tokens
        
        # Summarize if needed
        was_summarized = False
        if total_tokens > self.SUMMARIZE_THRESHOLD:
            doc_contexts = await self._summarize_documents(doc_contexts)
            was_summarized = True
            total_tokens = sum(d.token_count for d in doc_contexts)
        
        # Add web search if requested
        web_results = None
        if include_web_search and search_query:
            web_results = await self._perform_web_search(search_query)
        
        return PreparedContext(
            documents=doc_contexts,
            total_tokens=total_tokens,
            was_summarized=was_summarized,
            web_search_results=web_results
        )
    
    def _count_tokens(self, text: str) -> int:
        # Rough estimate: 4 chars per token
        return len(text) // 4
    
    async def _summarize_documents(
        self,
        docs: list[DocumentContext]
    ) -> list[DocumentContext]:
        # Use Haiku for cost-effective summarization
        summarized = []
        for doc in docs:
            if doc.token_count > 10000:  # Only summarize large docs
                summary = await self._summarize_single(doc.content)
                summarized.append(DocumentContext(
                    file_name=doc.file_name,
                    content=summary,
                    token_count=self._count_tokens(summary)
                ))
            else:
                summarized.append(doc)
        return summarized
    
    async def _summarize_single(self, content: str) -> str:
        response = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Summarize this document, preserving key facts, 
                figures, and conclusions. Be comprehensive but concise.
                
                DOCUMENT:
                {content}"""
            }]
        )
        return response.content[0].text
```

---

## Report Generation Logic

### LLM Service

```python
# backend/app/services/llm_service.py

from anthropic import Anthropic
from pydantic import BaseModel

class ReportSection(BaseModel):
    title: str
    content: str
    subsections: list['ReportSection'] = []

class GeneratedReport(BaseModel):
    title: str
    executive_summary: str
    sections: list[ReportSection]
    key_findings: list[str]
    recommendations: list[str]
    sources: list[str]
    
class GeneratedPresentation(BaseModel):
    title: str
    slides: list[dict]  # Each slide has 'title', 'content', 'notes'

class LLMService:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
    
    async def generate_report(
        self,
        context: str,
        custom_instructions: str,
        detail_level: str,
        web_search_results: str | None = None
    ) -> GeneratedReport:
        
        detail_guidance = {
            "executive": "Keep the report concise, 1-2 pages. Focus on high-level insights and actionable recommendations.",
            "standard": "Provide balanced detail, 3-5 pages. Include key findings with supporting evidence.",
            "comprehensive": "Create an in-depth analysis, 5-10 pages. Include full context, detailed findings, and thorough recommendations."
        }
        
        system_prompt = f"""You are an expert research analyst and report writer.
        
Your task is to synthesize the provided documents into a well-structured report.

DETAIL LEVEL: {detail_level.upper()}
{detail_guidance[detail_level]}

OUTPUT FORMAT: You must respond with valid JSON matching this structure:
{{
    "title": "Report Title",
    "executive_summary": "2-3 paragraph summary",
    "sections": [
        {{
            "title": "Section Title",
            "content": "Section content with full paragraphs",
            "subsections": []
        }}
    ],
    "key_findings": ["Finding 1", "Finding 2"],
    "recommendations": ["Recommendation 1", "Recommendation 2"],
    "sources": ["Source document 1", "Source document 2"]
}}

IMPORTANT:
- Write in professional, clear prose
- Support claims with evidence from the source documents
- Maintain objectivity
- Cite sources when referencing specific information"""

        user_content = f"""CUSTOM INSTRUCTIONS FROM USER:
{custom_instructions}

SOURCE DOCUMENTS:
{context}
"""
        
        if web_search_results:
            user_content += f"""

RECENT WEB SEARCH RESULTS (for additional context):
{web_search_results}
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[
                {"role": "user", "content": user_content}
            ],
            system=system_prompt
        )
        
        # Parse JSON response
        import json
        report_data = json.loads(response.content[0].text)
        return GeneratedReport(**report_data)
    
    async def generate_presentation(
        self,
        report: GeneratedReport,
        slide_count_min: int,
        slide_count_max: int,
        brand_config: dict
    ) -> GeneratedPresentation:
        
        system_prompt = f"""You are an expert presentation designer.

Convert the provided report into a compelling presentation.

SLIDE COUNT: Between {slide_count_min} and {slide_count_max} slides.

OUTPUT FORMAT: Respond with valid JSON:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "type": "title",
            "title": "Main Title",
            "subtitle": "Optional subtitle"
        }},
        {{
            "type": "section",
            "title": "Section Title"
        }},
        {{
            "type": "content",
            "title": "Slide Title",
            "bullets": ["Point 1", "Point 2", "Point 3"],
            "notes": "Speaker notes for this slide"
        }},
        {{
            "type": "key_findings",
            "title": "Key Findings",
            "findings": ["Finding 1", "Finding 2"]
        }},
        {{
            "type": "recommendations",
            "title": "Recommendations",
            "items": ["Rec 1", "Rec 2"]
        }},
        {{
            "type": "closing",
            "title": "Thank You",
            "contact": "Optional contact info"
        }}
    ]
}}

GUIDELINES:
- Start with title slide
- Use section dividers for major topics
- Keep bullet points concise (max 6 per slide)
- Include speaker notes for context
- End with recommendations and closing slide"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": f"""Create a presentation from this report:

REPORT:
Title: {report.title}
Executive Summary: {report.executive_summary}

Sections:
{self._format_sections(report.sections)}

Key Findings:
{chr(10).join(f'- {f}' for f in report.key_findings)}

Recommendations:
{chr(10).join(f'- {r}' for r in report.recommendations)}"""
            }],
            system=system_prompt
        )
        
        import json
        pres_data = json.loads(response.content[0].text)
        return GeneratedPresentation(**pres_data)
    
    def _format_sections(self, sections: list[ReportSection], level=0) -> str:
        result = []
        for section in sections:
            indent = "  " * level
            result.append(f"{indent}## {section.title}")
            result.append(f"{indent}{section.content[:500]}...")
            if section.subsections:
                result.append(self._format_sections(section.subsections, level + 1))
        return "\n".join(result)
```

---

## Presentation Generation Logic

### PPTX Renderer

```python
# backend/app/services/pptx_renderer.py

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RgbColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from io import BytesIO
from pathlib import Path

class PPTXRenderer:
    def __init__(self, brand_config: dict):
        self.brand = brand_config
        self.primary_color = self._hex_to_rgb(brand_config.get('primary_color', '#2563EB'))
        self.secondary_color = self._hex_to_rgb(brand_config.get('secondary_color', '#1E40AF'))
    
    def _hex_to_rgb(self, hex_color: str) -> RgbColor:
        hex_color = hex_color.lstrip('#')
        return RgbColor(
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    
    def render(self, presentation_data: dict, logo_path: Path | None = None) -> BytesIO:
        prs = Presentation()
        prs.slide_width = Inches(13.333)  # 16:9
        prs.slide_height = Inches(7.5)
        
        for slide_data in presentation_data['slides']:
            slide_type = slide_data.get('type', 'content')
            
            if slide_type == 'title':
                self._add_title_slide(prs, slide_data, logo_path)
            elif slide_type == 'section':
                self._add_section_slide(prs, slide_data)
            elif slide_type == 'content':
                self._add_content_slide(prs, slide_data)
            elif slide_type == 'key_findings':
                self._add_findings_slide(prs, slide_data)
            elif slide_type == 'recommendations':
                self._add_recommendations_slide(prs, slide_data)
            elif slide_type == 'closing':
                self._add_closing_slide(prs, slide_data, logo_path)
        
        # Save to BytesIO
        output = BytesIO()
        prs.save(output)
        output.seek(0)
        return output
    
    def _add_title_slide(self, prs: Presentation, data: dict, logo_path: Path | None):
        slide_layout = prs.slide_layouts[6]  # Blank
        slide = prs.slides.add_slide(slide_layout)
        
        # Background color
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.primary_color
        
        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5))
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get('title', 'Untitled')
        title_para.font.size = Pt(44)
        title_para.font.bold = True
        title_para.font.color.rgb = RgbColor(255, 255, 255)
        title_para.alignment = PP_ALIGN.CENTER
        
        # Subtitle
        if data.get('subtitle'):
            subtitle_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(0.8))
            subtitle_frame = subtitle_box.text_frame
            subtitle_para = subtitle_frame.paragraphs[0]
            subtitle_para.text = data['subtitle']
            subtitle_para.font.size = Pt(24)
            subtitle_para.font.color.rgb = RgbColor(255, 255, 255)
            subtitle_para.alignment = PP_ALIGN.CENTER
        
        # Logo
        if logo_path and logo_path.exists():
            slide.shapes.add_picture(str(logo_path), Inches(5.667), Inches(0.5), height=Inches(1))
    
    def _add_content_slide(self, prs: Presentation, data: dict):
        slide_layout = prs.slide_layouts[6]  # Blank
        slide = prs.slides.add_slide(slide_layout)
        
        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get('title', '')
        title_para.font.size = Pt(32)
        title_para.font.bold = True
        title_para.font.color.rgb = self.primary_color
        
        # Accent line under title
        line = slide.shapes.add_shape(
            1,  # Rectangle
            Inches(0.5), Inches(1.1),
            Inches(2), Inches(0.05)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = self.primary_color
        line.line.fill.background()
        
        # Bullet points
        content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12.333), Inches(5.5))
        tf = content_box.text_frame
        tf.word_wrap = True
        
        bullets = data.get('bullets', [])
        for i, bullet in enumerate(bullets):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = f"• {bullet}"
            p.font.size = Pt(20)
            p.space_after = Pt(12)
            p.level = 0
        
        # Speaker notes
        if data.get('notes'):
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = data['notes']
    
    def _add_section_slide(self, prs: Presentation, data: dict):
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)
        
        # Gradient-like effect (two rectangles)
        left_rect = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(6.667), Inches(7.5))
        left_rect.fill.solid()
        left_rect.fill.fore_color.rgb = self.primary_color
        left_rect.line.fill.background()
        
        # Section title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(3), Inches(6), Inches(1.5))
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get('title', 'Section')
        title_para.font.size = Pt(40)
        title_para.font.bold = True
        title_para.font.color.rgb = RgbColor(255, 255, 255)
    
    def _add_findings_slide(self, prs: Presentation, data: dict):
        # Similar to content slide but styled for findings
        self._add_content_slide(prs, {
            'title': data.get('title', 'Key Findings'),
            'bullets': data.get('findings', [])
        })
    
    def _add_recommendations_slide(self, prs: Presentation, data: dict):
        self._add_content_slide(prs, {
            'title': data.get('title', 'Recommendations'),
            'bullets': data.get('items', [])
        })
    
    def _add_closing_slide(self, prs: Presentation, data: dict, logo_path: Path | None):
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)
        
        # Background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.secondary_color
        
        # Thank you text
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.8), Inches(12.333), Inches(1.5))
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get('title', 'Thank You')
        title_para.font.size = Pt(48)
        title_para.font.bold = True
        title_para.font.color.rgb = RgbColor(255, 255, 255)
        title_para.alignment = PP_ALIGN.CENTER
        
        # Contact info
        if data.get('contact'):
            contact_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.5), Inches(12.333), Inches(0.8))
            contact_frame = contact_box.text_frame
            contact_para = contact_frame.paragraphs[0]
            contact_para.text = data['contact']
            contact_para.font.size = Pt(20)
            contact_para.font.color.rgb = RgbColor(255, 255, 255)
            contact_para.alignment = PP_ALIGN.CENTER
```

---

## Configuration & Environment

### Environment Variables

```bash
# .env.example

# ===================
# SUPABASE
# ===================
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...  # Only for backend

# ===================
# GOOGLE DRIVE
# ===================
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}  # Full JSON, base64 encoded
# OR path to file:
GOOGLE_SERVICE_ACCOUNT_PATH=/secrets/google-sa.json

# ===================
# API KEYS (stored in DB per-org, but fallback defaults)
# ===================
# These are optional defaults; each org provides their own
DEFAULT_ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_SERPER_API_KEY=...

# ===================
# APP CONFIG
# ===================
ENVIRONMENT=development  # development | staging | production
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,https://reportgen.nitrovialabs.com

# ===================
# STORAGE
# ===================
# Supabase Storage bucket names
UPLOAD_BUCKET=uploads
OUTPUT_BUCKET=generated-reports

# ===================
# RATE LIMITS
# ===================
MAX_CONCURRENT_GENERATIONS=10
MAX_FILE_SIZE_MB=50
MAX_FILES_PER_REPORT=20
```

### Backend Config

```python
# backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    log_level: str = "INFO"
    
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    
    # Google Drive
    google_service_account_json: str | None = None
    google_service_account_path: str | None = None
    
    # Defaults
    default_anthropic_api_key: str | None = None
    default_serper_api_key: str | None = None
    
    # CORS
    cors_origins: str = "http://localhost:5173"
    
    # Storage
    upload_bucket: str = "uploads"
    output_bucket: str = "generated-reports"
    
    # Limits
    max_concurrent_generations: int = 10
    max_file_size_mb: int = 50
    max_files_per_report: int = 20
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---

## Deployment Guide

### Prerequisites

1. **Accounts needed**:
   - Supabase (free tier)
   - Railway (free tier)
   - Cloudflare Pages (free)
   - Google Cloud Console (for Drive API)

2. **Local tools**:
   - Python 3.11+
   - Node.js 18+
   - Git

### Step 1: Supabase Setup

```bash
# 1. Create project at supabase.com
# 2. Note down:
#    - Project URL
#    - Anon key (public)
#    - Service key (secret)

# 3. Run database migrations
# Go to SQL Editor in Supabase dashboard
# Paste and run the schema from "Database Schema" section above

# 4. Configure Auth
# Settings → Authentication → Providers
# Enable: Email, Google

# 5. Configure Storage
# Storage → Create buckets:
# - "uploads" (private)
# - "generated-reports" (private)
```

### Step 2: Google Drive Setup

```bash
# 1. Go to Google Cloud Console
# 2. Create new project: "Report Generator"
# 3. Enable Google Drive API
# 4. Create Service Account:
#    - Name: report-generator-sa
#    - Download JSON key
# 5. Share Drive folder with service account email

# 6. Encode service account JSON for env var:
cat service-account.json | base64 -w 0
# Store this output as GOOGLE_SERVICE_ACCOUNT_JSON
```

### Step 3: Backend Deployment (Railway)

```bash
# 1. Push backend to GitHub repo

# 2. Connect to Railway:
#    - New Project → Deploy from GitHub
#    - Select repo, set root to /backend

# 3. Configure environment:
#    - Add all env vars from .env.example
#    - Railway will auto-detect Dockerfile

# 4. Set up health check:
#    - Health check path: /health

# 5. Note the deployment URL
```

### Step 4: Frontend Deployment (Cloudflare Pages)

```bash
# 1. Push frontend to GitHub repo

# 2. Connect to Cloudflare Pages:
#    - Pages → Create project → Connect to Git
#    - Select repo
#    - Framework preset: Vite
#    - Build command: npm run build
#    - Output directory: dist
#    - Root directory: frontend

# 3. Configure environment variables:
#    VITE_SUPABASE_URL=...
#    VITE_SUPABASE_ANON_KEY=...
#    VITE_API_URL=https://your-railway-url.railway.app

# 4. Custom domain (optional):
#    - Add CNAME: reportgen.nitrovialabs.com
```

### Step 5: Post-Deployment Verification

```bash
# 1. Check backend health
curl https://your-railway-url/health

# 2. Check frontend loads
# Visit https://reportgen.nitrovialabs.com

# 3. Test auth flow
# - Sign up with email
# - Check Supabase Auth for user

# 4. Test file upload
# - Upload a small PDF
# - Check Supabase Storage

# 5. Test report generation (with API key)
# - Configure org with Anthropic key
# - Generate test report
```

---

## Maintenance Runbook

### For Client Handoff

```markdown
# Report Generator - Maintenance Guide

## System Health Checks

### Daily (Automated)
- UptimeRobot monitors: reportgen.nitrovialabs.com
- You'll receive email if site goes down

### Weekly (Manual, 5 min)
1. Log into Railway dashboard
2. Check "Deployments" - should show "Active"
3. Check "Metrics" - memory under 512MB is healthy
4. Check "Logs" - no repeated errors

## Common Issues & Fixes

### "Site won't load"
1. Check Railway deployment status
2. If crashed, click "Redeploy" button
3. If still failing, contact developer

### "Report generation stuck"
1. Check if API key is valid (Settings page)
2. Try generating with a smaller file
3. Check Railway logs for errors

### "Google Drive not showing files"
1. Ensure folder is shared with service account
2. Check Settings → Google Drive connection
3. Service account email: report-generator-sa@...

### "File upload fails"
1. Check file is under 50MB
2. Ensure file is PDF, DOCX, XLSX, or PPTX
3. Check Supabase Storage quota

## Restarting the System

### Backend (Railway)
1. Go to railway.app, log in
2. Select "report-generator" project
3. Go to Deployments
4. Click "Redeploy" on latest deployment
5. Wait 2-3 minutes for restart

### If Railway Asks for Payment
- Free tier: 500 hours/month
- If exceeded, either:
  - Wait until next month
  - Upgrade to $5/month hobby plan
  - Contact developer

## Updating API Keys

### Anthropic API Key
1. Get new key from console.anthropic.com
2. Login to Report Generator
3. Settings → API Keys → Update Anthropic Key

### Serper API Key
1. Get new key from serper.dev
2. Settings → API Keys → Update Serper Key

## Monthly Tasks
1. Review Railway usage (stay under 500 hours)
2. Check Supabase storage (under 1GB free)
3. Review API costs at console.anthropic.com

## Emergency Contact
Developer: [Your contact info]
Response time: 24-48 hours
```

---

## Cost Projections

### Monthly Infrastructure

| Service | Free Tier Limit | Expected Usage | Cost |
|---------|-----------------|----------------|------|
| Railway | 500 hrs/month | ~400 hrs | $0 |
| Supabase DB | 500MB | ~50MB | $0 |
| Supabase Auth | 50K MAU | ~10 users | $0 |
| Supabase Storage | 1GB | ~500MB | $0 |
| Cloudflare Pages | Unlimited | - | $0 |
| **Total Infrastructure** | | | **$0-5** |

### Monthly LLM Costs (Client Pays)

| Metric | Value | Cost |
|--------|-------|------|
| Reports/month | 150 | - |
| Avg input tokens/report | 20,000 | - |
| Avg output tokens/report | 4,000 | - |
| Total input tokens | 3M | ~$9 |
| Total output tokens | 600K | ~$9 |
| Web searches (30%) | 45 | $0 (free tier) |
| **Total LLM** | | **$15-25** |

### Client's Total Monthly Cost

```
Infrastructure (paid by you): $0-5
LLM API (paid by client):     $15-25
────────────────────────────────────
Total:                        $15-30/month
```

**Value proposition**: 150 reports that would take hours manually, for <$30/month.

---

## Next Steps

1. [ ] Review and approve this specification
2. [ ] Set up Supabase project
3. [ ] Set up Google Cloud service account
4. [ ] Initialize Git repository
5. [ ] Begin backend development (Week 1-2)
6. [ ] Begin frontend development (Week 2-3)
7. [ ] Integration testing (Week 3)
8. [ ] Deployment and handoff (Week 4)

---

## Questions Before Development

1. **Organization name**: What should the default org be called?
2. **Domain**: Will you use a subdomain like `reportgen.nitrovialabs.com` or separate domain?
3. **Logo**: Does the client have a logo file for branding?
4. **Sample files**: Can you get 2-3 sample documents from the client for testing?
