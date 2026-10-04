# AquaLens

Mobile-first PWA for AI-assisted, human-verified OneAquaHealth stream assessments.
Primary track: Track 3 (AI-Supported Assessment). Secondary: Track 7 (FHIR).

## Prerequisites

- Python 3.11+
- Node.js 20+
- Copy `.env.example` to `.env` and fill values (never commit `.env`)

## Backend (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000  
Health: http://127.0.0.1:8000/health  
Interactive docs: http://127.0.0.1:8000/docs

Tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

## Frontend (Windows PowerShell)

```powershell
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173  

The Vite dev server proxies `/health` and `/api` to the backend on port 8000.

Build / lint:

```powershell
cd frontend
npm run build
npm run lint
```

## Scaffold status

Through Prompt 2:
- `/health`, DB models, PWA shell
- `GET /api/form-schema`, sites (6 DEMO seeded), observations create/get/list
- Local photo storage with resize + EXIF strip (Supabase adapter selectable via env)

AI analyze, validation/risk, and FHIR come in later prompts.

## Privacy

No names or emails. Strip EXIF on photos. Never commit secrets.

## Expert PIN (demo-only)

The expert review route (`/expert`) uses a PIN sent as the `X-Expert-Pin` header. This is **demo-only authentication** — real authentication (OAuth, session, or signed tokens) is future work. The PIN is configured via the `EXPERT_PIN` environment variable in `.env` (default: `change-me`).
