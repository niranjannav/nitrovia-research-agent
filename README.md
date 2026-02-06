# Research Report Generator

Automated research report and presentation generation from uploaded documents.

## Features

- **Document Upload**: Support for PDF, DOCX, XLSX, PPTX files
- **Google Drive Integration**: Import files directly from Google Drive
- **AI-Powered Generation**: Uses Claude to analyze documents and generate reports
- **Multiple Output Formats**: PDF, DOCX, and PPTX presentations
- **Configurable Detail Levels**: Executive, Standard, or Comprehensive reports

## Tech Stack

- **Backend**: FastAPI (Python) on Railway
- **Frontend**: React + Vite + Tailwind CSS on Cloudflare Pages
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth
- **Storage**: Supabase Storage
- **LLM**: Anthropic Claude

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account
- Anthropic API key
- Google Cloud service account (for Drive integration)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with your credentials
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with your credentials
npm run dev
```

## Environment Variables

See `.env.example` for required environment variables.

### Backend
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `GOOGLE_SERVICE_ACCOUNT_JSON` - Base64 encoded Google service account JSON

### Frontend
- `VITE_SUPABASE_URL` - Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anonymous key
- `VITE_API_URL` - Backend API URL

## Project Structure

```
nitrovia-research-agent/
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── models/       # Database & Pydantic models
│   │   ├── services/     # Business logic
│   │   ├── templates/    # PDF templates
│   │   └── utils/        # Helpers
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/   # React components
│       ├── pages/        # Page components
│       ├── hooks/        # Custom hooks
│       ├── stores/       # Zustand stores
│       ├── services/     # API services
│       └── types/        # TypeScript types
└── docs/
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API docs.

## Deployment

See [MAINTENANCE.md](./MAINTENANCE.md) for deployment and maintenance instructions.

## License

Proprietary - All rights reserved.
