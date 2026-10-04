# AquaLens — Agent Instructions

## Mission
Hackathon project for the OneAquaHealth IEEE Global Hackathon 2026 (submit by the evening of 30 Sep 2026, IST).
Primary track: Track 3 (AI-Supported Assessment). Secondary: Track 7 (FHIR).
Optimise for: a working end-to-end demo, clarity, and responsible AI, not feature count.
Before coding read every file in docs/. docs/02_form_schema_and_ai.md is the source of truth for fields, answer codes, AI output contract and validation rules.

## Product
Mobile-first PWA. A citizen uploads stream photos; AI SUGGESTS answers to the official OneAquaHealth assessment questions with confidence and a reason; the citizen confirms or edits; validation rules flag inconsistencies; flagged records go to an expert queue; every record can be exported as FHIR and produces a plain-language, indicative One Health risk note.

## Stack (all free tiers / open source)
Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, pytest, httpx, Pillow. SQLite locally, Postgres (Supabase) in production via DATABASE_URL.
Frontend: Vite, React, TypeScript, Tailwind, react-router, react-leaflet, vite-plugin-pwa.
AI: Groq vision model through an adapter (chain: groq -> cache -> mock).
External: Open-Meteo (weather), OpenStreetMap Overpass (water-body check), public HAPI FHIR test server. fhir.resources for FHIR models.

## Non-negotiable rules
1. Human in the loop. AI output is only a suggestion. Never store an AI value as final until the user accepts or edits it. Every stored field has a source: ai_accepted | ai_edited | human | unanswered.
2. Every AI suggestion has value, confidence (0-1) and a one-sentence reason. "not_sure" is always a valid value. Never invent values.
3. Human-only fields (no AI): water_height, feelings, overall_assessment. The user chooses the overall rating BEFORE seeing the advisory comparison.
4. Risk notes are rule-based and transparent: list the reasons, and always show "Indicative only, not a safety certification". Never accuse a person or company of discharging anything; describe only what is visible.
5. Privacy: strip EXIF on client and server, collect no names or emails, never send photos, free text or feelings to the public FHIR server, never commit secrets (.env.example only).
6. Zero cost: no paid services. Put every external service behind an adapter (AI, weather, water check, storage, FHIR server).
7. External calls need timeouts, at most one retry and graceful degradation. The app must still work with AI or weather down (manual entry).
8. Data honesty: seeded data has is_synthetic=true and the UI shows "Demo data".
9. Do not copy the official app's images or long text. Write original help text.
10. Code quality: type hints/TypeScript everywhere, small modules, validation and risk logic as pure functions with table-driven tests, no TODO or placeholder implementations, no dead code. Say why before adding any dependency.
11. UX: mobile-first, 44px touch targets, plain language, labelled inputs, good contrast, visible loading and error states.
12. Workflow: for anything non-trivial write a short plan first. After each task run tests and type checks, summarise what changed and how to verify it. If the docs conflict or an item is marked PENDING, ask instead of guessing.

## Commands (Windows PowerShell)
Backend: cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn app.main:app --reload; pytest
Frontend: cd frontend; npm install; npm run dev; npm run build; npm run lint

## Definition of done (MVP)
Photo -> AI suggestions -> user confirms -> validation flags -> risk notes -> save -> map pin -> expert queue -> FHIR bundle validates and POSTs to the test server. Works on a phone, deployed on free hosting, with README, architecture diagram and seeded demo data.
