# AquaLens — Implementation Plan (Prompt 0)

Source of truth for fields, AI contract and validation: `docs/02_form_schema_and_ai.md`.  
Stack and non-negotiables: `AGENTS.md`. Product/API intent: `docs/01_PRD_TRD_Workflow.md`. Decisions: `docs/04_decisions.md`.

**Status:** Prompt 2 complete (form schema, sites, observations, storage). Next: Prompt 3 (AI chain).

---

## 1) Product understanding (10 lines)

1. AquaLens is a mobile-first PWA companion for OneAquaHealth stream assessments (Track 3 primary, Track 7 FHIR secondary).
2. A citizen picks or adds a site (GPS suggests nearest demo sites), uploads four photos (upstream, downstream, context, biodiversity; video skipped in MVP), and confirms facing-downstream.
3. AI suggests answers for eligible fields only: each suggestion is `{value, confidence, reason}`; `not_sure` is always valid; never invent.
4. Human-only fields: `water_height`, `feelings`, `overall_assessment` (user rates overall **before** seeing the advisory comparison).
5. Every stored answer has a provenance source: `ai_accepted | ai_edited | human | unanswered` — AI values are never saved as final until the user accepts or edits.
6. Pure validation rules flag contradictions and force expert review for high-impact yeses (pipes, sewage, construction, cuts, invasive).
7. Rule-based risk notes (contact-safety for people/pets; ecosystem pressure) are Low/Moderate/High with reasons and always labelled “Indicative only, not a safety certification”.
8. Confirmed observations appear on a map; flagged ones go to a PIN-protected expert queue (approve/correct).
9. Each observation can be exported as a FHIR R4 transaction Bundle and POSTed to a public HAPI test server (no photos, free text or feelings).
10. Zero-cost adapters (Groq→cache→mock, Open-Meteo, Overpass, local/Supabase storage, FHIR); app works when AI or weather is down via manual entry.

---

## 2) Final repo structure

```
aqualens/
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── docs/
│   ├── 00_hackathon_brief.md
│   ├── 01_PRD_TRD_Workflow.md
│   ├── 02_form_schema_and_ai.md
│   ├── 03_official_app_notes.md
│   ├── 04_decisions.md
│   └── 05_implementation_plan.md          # this file (keep current)
├── backend/
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI app, CORS, create tables
│   │   ├── config.py                      # pydantic-settings from env
│   │   ├── db.py                          # engine, Session, Base
│   │   ├── models.py                      # SQLAlchemy: Site, Observation, Review
│   │   ├── schemas.py                     # Pydantic request/response models
│   │   ├── form_schema.py                 # single source of truth for fields
│   │   ├── validation.py                  # pure Flag rules (docs/02 §4)
│   │   ├── risk.py                        # contact + ecosystem notes + overall suggest
│   │   ├── fhir_mapper.py                 # fhir.resources Bundle build/send
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                    # AIProvider protocol
│   │   │   ├── groq_provider.py
│   │   │   ├── cache_provider.py
│   │   │   ├── mock_provider.py
│   │   │   ├── chain.py                   # groq → cache → mock
│   │   │   ├── prompts.py
│   │   │   ├── merge.py                   # upstream/downstream merge
│   │   │   └── models.py                  # suggestion Pydantic models
│   │   ├── adapters/
│   │   │   ├── storage.py                 # local folder | Supabase
│   │   │   └── fhir_client.py             # POST to FHIR_SERVER_URL
│   │   ├── context/
│   │   │   ├── weather.py                 # Open-Meteo
│   │   │   └── water_check.py             # Overpass
│   │   └── routers/
│   │       ├── health.py
│   │       ├── form_schema.py
│   │       ├── sites.py
│   │       ├── analyze.py
│   │       ├── observations.py
│   │       ├── queue.py
│   │       └── fhir.py
│   └── tests/
│       ├── conftest.py
│       ├── test_form_schema.py
│       ├── test_sites.py
│       ├── test_storage.py
│       ├── test_ai_merge.py
│       ├── test_validation.py
│       ├── test_risk.py
│       └── test_fhir_mapper.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts                     # + vite-plugin-pwa
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/                            # PWA icons (placeholders ok)
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                        # routes + bottom nav
│       ├── api/client.ts
│       ├── types/
│       ├── components/                    # shared UI (labels, badges, flags)
│       ├── pages/
│       │   ├── Home.tsx
│       │   ├── Observe/                   # wizard steps
│       │   ├── Result.tsx
│       │   ├── MapPage.tsx
│       │   └── Expert/
│       └── lib/                           # resize/EXIF strip, geo helpers
├── scripts/
│   ├── groq_photo_test.py                 # already present
│   ├── warm_cache.py
│   ├── seed.py
│   ├── warm_servers.py
│   └── smoke_test.py
├── test_photos/                           # local Day-1 test only (gitignored content)
└── labels.csv
```

Personal / gitignored (not in public structure intent): `_my_notes/`, `START_HERE.md`, `.env`, `uploads/`, `cache/`, `docs/reference/`.

---

## 3) Database schema

SQLite locally; Postgres via `DATABASE_URL` in production. Types below are logical; SQLAlchemy maps them.

### `sites`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID / TEXT PK | |
| `name` | TEXT NOT NULL | e.g. “Demo Creek North” |
| `code` | TEXT NOT NULL UNIQUE | e.g. `DEMO-01` (never real official codes) |
| `lat` | FLOAT NOT NULL | |
| `lon` | FLOAT NOT NULL | |
| `is_demo` | BOOLEAN NOT NULL DEFAULT true | |
| `created_at` | TIMESTAMPTZ NOT NULL | |

### `observations`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID / TEXT PK | |
| `site_id` | FK → sites.id | |
| `user_lat`, `user_lon` | FLOAT NULL | may be null if GPS denied |
| `facing_downstream` | BOOLEAN NOT NULL | left/right mapping gate |
| `captured_at` | TIMESTAMPTZ NOT NULL | |
| `photos_json` | JSON | `{upstream, downstream, context, biodiversity}` → storage paths/URLs |
| `answers_json` | JSON | field_id → final value (or null) |
| `ai_suggestions_json` | JSON | field_id → `{value, confidence, reason}` as returned at analyze time |
| `field_sources_json` | JSON | field_id → `ai_accepted \| ai_edited \| human \| unanswered` |
| `flags_json` | JSON | list of Flag objects from validation |
| `needs_expert` | BOOLEAN NOT NULL | |
| `status` | TEXT NOT NULL | `draft \| confirmed \| flagged \| approved \| corrected` |
| `overall_user` | TEXT NULL | `good \| moderate \| poor` |
| `overall_suggested` | TEXT NULL | advisory from pressure count |
| `risk_contact` | TEXT NULL | `low \| moderate \| high` |
| `risk_ecosystem` | TEXT NULL | `low \| moderate \| high` |
| `risk_reasons_json` | JSON | `{contact: [...], ecosystem: [...]}` |
| `feelings_json` | JSON | joy/serenity/anger/fear: `{value: 1-5\|null, na: bool}` — never sent to FHIR |
| `is_synthetic` | BOOLEAN NOT NULL DEFAULT false | UI shows “Demo data” when true |
| `fhir_sent_at` | TIMESTAMPTZ NULL | |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `reviews`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID / TEXT PK | |
| `observation_id` | FK → observations.id | |
| `decision` | TEXT NOT NULL | `approved \| corrected` |
| `corrections_json` | JSON | field_id → new value (empty if approve-only) |
| `reviewer_note` | TEXT NULL | no PII; not sent to public FHIR as free-text dump of feelings |
| `reviewed_at` | TIMESTAMPTZ NOT NULL | |

### Photo / AI cache (filesystem or object storage, not necessarily SQL)
- Dev: `uploads/{observation_or_temp_id}/…`, `cache/ai/{sha256}_{role}.json`
- Prod: Supabase Storage via storage adapter; AI cache can remain local disk or a `ai_cache` table if needed for multi-instance — **proposal:** start with local/file cache keyed by image hash+role; revisit if Render is multi-instance.

---

## 4) API endpoints (request / response shapes)

All JSON unless noted. Errors: `{ "detail": string }` (FastAPI default). Auth: only expert routes use header `X-Expert-Pin: <EXPERT_PIN>` (demo-only).

### `GET /health`
**Response 200**
```json
{ "status": "ok", "ai_chain": ["groq", "cache", "mock"], "db": "ok" }
```

### `GET /api/form-schema`
**Response 200**
```json
{
  "version": "1",
  "fields": [
    {
      "id": "water_aspect",
      "group": "questions_2",
      "question": "How does the water look?",
      "help": "Original plain-language help (not copied from the official app).",
      "values": ["A", "B", "C", "D", "not_sure"],
      "value_labels": { "A": "Clear", "B": "Muddy / turbid", "C": "Foam", "D": "Colours / altered", "not_sure": "Not sure" },
      "ai_role": "suggest",
      "pending": false
    }
  ],
  "pending_notes": {
    "habitats_present": "Types A–E unknown; presence-only",
    "natural_debris_present": "Types A–C unknown; presence-only",
    "water_height": "Unit unconfirmed; label cm (to be confirmed)",
    "feelings": "Range assumed 1–5"
  }
}
```
`ai_role`: `suggest | human_only | candidates_only`.

### `GET /api/sites?lat=&lon=`
**Query:** `lat`, `lon` optional. If present, sort by Haversine distance; if absent, return all (or demo list) without distance.
**Response 200**
```json
{
  "sites": [
    {
      "id": "…",
      "name": "Demo Creek North",
      "code": "DEMO-01",
      "lat": 12.97,
      "lon": 77.59,
      "is_demo": true,
      "distance_m": 240.5
    }
  ]
}
```
`distance_m` omitted or null when lat/lon not provided. Never show NaN.

### `POST /api/sites`
**Request**
```json
{ "name": "My informal site", "code": "LOCAL-01", "lat": 12.98, "lon": 77.60 }
```
**Response 201:** same shape as one site object (without requiring distance).

### `POST /api/analyze`
**Request:** `multipart/form-data`
- files: `photo_upstream`, `photo_downstream`, `photo_context`, `photo_biodiversity` (all recommended; missing → degrade)
- optional: `facing_downstream` (bool string) — **proposal:** analyze returns image-as-seen margins; mapping happens on the client after confirmation (per TRD). Facing may be ignored at analyze time.

**Response 200 (success)**
```json
{
  "status": "ok",
  "suggestions": {
    "water_aspect": { "value": "A", "confidence": 0.82, "reason": "Water surface looks clear with visible bed." }
  },
  "upstream_vs_downstream": "Upstream looks clearer than downstream.",
  "needs_expert_hints": ["draining_pipes"],
  "provider_used": "groq"
}
```
**Response 200 (degraded)**
```json
{
  "status": "ai_unavailable",
  "suggestions": {},
  "message": "AI is unavailable; please answer manually."
}
```
Never persists an observation.

### `POST /api/observations/evaluate`
Dry run: flags, risk, suggested overall. Does not save.
**Request**
```json
{
  "site_id": "…",
  "user_lat": 12.97,
  "user_lon": 77.59,
  "facing_downstream": true,
  "answers": { "water_flow": "D", "water_height": 12, "overall_assessment": "good" },
  "field_sources": { "water_flow": "ai_accepted", "water_height": "human" },
  "ai_suggestions": {
    "water_aspect": { "value": "B", "confidence": 0.75, "reason": "…" }
  }
}
```
**Response 200**
```json
{
  "flags": [
    {
      "code": "dry_vs_height",
      "fields": ["water_flow", "water_height"],
      "message": "Flow is marked dry but water height is greater than zero.",
      "severity": "error",
      "needs_expert": false
    }
  ],
  "needs_expert": true,
  "overall_suggested": "moderate",
  "overall_pressure_count": 4,
  "overall_mismatch_levels": 2,
  "risk": {
    "contact": { "level": "high", "reasons": ["…"] },
    "ecosystem": { "level": "moderate", "reasons": ["…"] },
    "disclaimer": "Indicative only, not a safety certification"
  },
  "context": {
    "rainfall_48h_mm": 12.3,
    "temperature_c": 28.1,
    "water_nearby": "yes"
  }
}
```
Weather/water failures → `null` / `"unknown"`; never invent flags from unknown water check.

### `POST /api/observations`
**Request:** evaluate payload plus photos already uploaded **or** multipart with photos + JSON fields.
**Proposal for MVP:** two-step — client uploads photos as part of this multipart POST; server resizes, strips EXIF, stores, then evaluates and saves.

**Request (multipart or JSON+URLs):** same fields as evaluate, plus optional `is_synthetic` (false for citizen path), and photo files or prior temp keys.

**Response 201**
```json
{
  "id": "…",
  "status": "flagged",
  "needs_expert": true,
  "flags": […],
  "risk": { … },
  "overall_user": "good",
  "overall_suggested": "poor",
  "is_synthetic": false
}
```

### `GET /api/observations`
**Query (optional):** `bbox=minLon,minLat,maxLon,maxLat`, `needs_expert=true`, `risk=high`, `status=…`
**Response 200**
```json
{
  "observations": [
    {
      "id": "…",
      "site_id": "…",
      "site_name": "Demo Creek North",
      "lat": 12.97,
      "lon": 77.59,
      "status": "flagged",
      "needs_expert": true,
      "risk_contact": "high",
      "risk_ecosystem": "moderate",
      "overall_user": "moderate",
      "is_synthetic": true,
      "captured_at": "2026-09-19T10:00:00Z"
    }
  ]
}
```

### `GET /api/observations/{id}`
**Response 200:** full observation including `answers`, `ai_suggestions`, `field_sources`, `flags`, `risk_*`, `feelings`, `photos` (URLs), `reviews` summary.

### `GET /api/queue`
**Headers:** `X-Expert-Pin`
**Response 200**
```json
{
  "items": [
    {
      "id": "…",
      "site_name": "…",
      "flags": […],
      "needs_expert": true,
      "status": "flagged",
      "captured_at": "…"
    }
  ]
}
```
**401** if PIN wrong.

### `POST /api/observations/{id}/review`
**Headers:** `X-Expert-Pin`  
**Request**
```json
{
  "decision": "corrected",
  "corrections": { "draining_pipes": "no" },
  "reviewer_note": "Pipe is a drain cover, not a discharge."
}
```
**Response 200:** updated observation (`status`: `approved` or `corrected`).

### `GET /api/observations/{id}/fhir`
**Response 200**
```json
{
  "bundle": { "resourceType": "Bundle", "type": "transaction", "entry": […] },
  "excluded": ["photos", "feelings", "free_text"]
}
```

### `POST /api/observations/{id}/fhir/send`
**Response 200**
```json
{
  "ok": true,
  "http_status": 200,
  "server_response": { },
  "fhir_sent_at": "2026-09-19T12:00:00Z"
}
```
Bundle sent must omit photos, feelings, invasive free text, and other free text.

---

## 5) Milestones (build order) with acceptance tests

Aligned with `_my_notes/prompts.md` Prompts 1–10 and `docs/01` timeline.

| # | Milestone | Deliverable | Acceptance test |
|---|---|---|---|
| M0 | Day-1 Groq photo test | `scripts/groq_photo_test.py` + labelled photos | ≥95% JSON parse; high-confidence fields ~≥80% agree with your labels; blurry/flow stay not_sure/low; no false-confident pipe/sewage; fits TPM after resize |
| M1 | Scaffold | Monorepo as §2; `/health`; empty models; PWA shell + bottom nav | `pytest` passes smoke; `npm run build`; both apps start; home shows health OK |
| M2 | Form schema, sites, observations, storage | `form_schema.py`, sites CRUD/list-by-distance, observation create/get/list, Pillow EXIF strip | Schema rejects illegal values; sites sort by distance; GPS-denied list has no NaN; storage adapter test strips EXIF |
| M3 | AI chain + `/api/analyze` | Groq/cache/mock chain, merge rules, never saves | Mock tests: agree→lower confidence; disagree→not_sure; any yes on pipe/sewage/construction wins; invalid AI→not_sure; no real Groq in CI |
| M4 | Validation, risk, weather, water | Pure functions + evaluate endpoint | ≥30 table-driven cases covering docs/02 §4; weather/water timeout degrade; unknown water never flags |
| M5 | FHIR | Mapper + get/send endpoints | Bundle validates with `fhir.resources`; snapshot of structure; sent payload has no photos/feelings/free text; test server POST returns status |
| M6 | Frontend capture | Site + photos + analyze | On phone/LAN: GPS/deny paths work; 4 slots resize to ~1024; analyze progress; `ai_unavailable` continues manually |
| M7 | Frontend review + save | Accept/Edit/Not sure, evaluate flags, overall-first, feelings, save | Source badges correct; overall comparison only after pick; two-level mismatch explained; POST saves with sources |
| M8 | Result, map, expert | Risk notes, FHIR UI, map filters, PIN queue | Pin colours by risk; demo labelled; approve/correct updates status; FHIR send shows server body |
| M9 | Seed + deploy | 25 synthetic obs, warm scripts, free hosting | Seed `is_synthetic=true`; smoke script against deployed URL; `/health` warm works; no secrets in repo |
| M10 | Polish + submit assets | README Mermaid, Devpost draft, demo script | Mobile + PWA install check; judging gaps listed/fixed in scope; video click path runnable on live link |

**Never cut:** AI confirm loop, validation flags, FHIR export, map, expert queue, deployed demo, 3–5 min video.  
**Cut order if behind:** wellbeing chart → expert Correct (keep Approve) → upstream-vs-downstream note → biodiversity analysis.

---

## 6) Conflicts, gaps, risks (esp. PENDING) and proposals

### Conflicts / inconsistencies between docs

| Issue | Where | Proposal |
|---|---|---|
| **Field source vocabulary** | AGENTS/PRD: `ai_accepted \| ai_edited \| human \| unanswered`. docs/02 §6: `ai_suggested_human_confirmed`, `human_entered`, `not_answered` (no edited split). | **Use AGENTS/PRD four values** in DB, API and FHIR Provenance. UI labels can read “AI accepted”, “AI edited”, “Entered by you”, “Not answered”. Update docs/02 §6 when implementing. |
| **AI call grouping** | docs/02 §3: “one request per photo **group**” (upstream+downstream together). TRD + Prompt 3: **one call per photo by role**, then merge. | **One call per photo role** (token TPM). Merge in `ai/merge.py`. Keep Group A/B/C field lists from docs/02 as which fields each role may answer. |
| **Provenance vs “candidates_only”** | Invasive species: AI candidates, expert-confirmed. | Store user/expert decision as `human` or `ai_edited`; keep candidate list only in `ai_suggestions_json`, never as silent final. |
| **Deadline wording** | AGENTS: evening 30 Sep. Brief: Devpost 1 Oct 09:30 IST. | Submit **evening of 30 Sep IST** as planned. |
| **Team required?** | docs/00 open. | Out of code scope; confirm Rules/Slack before submit. Does not block build. |

### PENDING items (docs/02, 03) — do not guess letters

| PENDING | Proposal until confirmed |
|---|---|
| Habitats types A–E | Boolean `habitats_present` only (`yes/no/not_sure`). Mark `pending` in form-schema. |
| Natural debris types A–C | Boolean `natural_debris_present` only. Same. |
| Water height unit | Number input; label **“cm (unit to be confirmed)”**; soft flag if `< 0` or `> 300` (config constant `WATER_HEIGHT_SOFT_MAX=300`). |
| Feelings slider range | Integers **1–5**, default 3, each with Not applicable (`value: null`, `na: true`). |
| Official app API/export | Standalone companion; export FHIR (+ optional CSV later). Never submit into official app. |

### Thresholds not specified in docs — proposed defaults (tunable)

| Rule | Proposed default | Rationale |
|---|---|---|
| GPS vs site distance flag | **> 500 m** → flag (severity warning; does not alone force expert) | Urban sites close together; 500 m catches wrong-site picks without nagging walkers |
| AI confidence low | **< 0.5** → flag (docs/02 §4.8) | As written |
| Aspect vs AI turbidity | AI confidence **≥ 0.7** and user clear → flag | As written |
| Overall pressure bands | 0–2 good, 3–5 moderate, 6+ poor | As written |
| Contact-safety High | Any of: sewage=yes, pipes=yes, aspect foam/colour, or (turbid + rainfall_48h ≥ 10 mm) | Transparent, visible-only |
| Contact-safety Moderate | Turbid or stagnant/intermittent without the High triggers | |
| Ecosystem High | ≥3 of: artificial bed/bank, impervious L/R, no veg L/R, barrier, construction, cuts | Aligns with pressure counting spirit |
| Rate limit `/api/analyze` | e.g. **10/min per IP** (middleware) | Demo abuse protection |

### Product / delivery risks

| Risk | Mitigation |
|---|---|
| Groq quality or TPM | M0 photo test; chain groq→cache→mock; `SLEEP_SECONDS`; resize 1024; warm_cache for demo |
| Free hosts sleep | `/health` + `warm_servers.py` before demos/judging |
| FHIR `$validate` / server quirks | Build one Observation first; report offline vs server validation gaps in README |
| Scope creep | Non-goals + cut order above |
| PENDING form details | Presence-only / soft unit until confirmed in official app |
| Left/right bank errors | Ask facing-downstream; map image L/R → stream L/R only if true; else leave for user |
| Privacy leak to FHIR | Explicit exclude list in mapper tests |
| Dual EXIF strip | Client canvas JPEG + server Pillow — both required |

### Open questions for you (review)

1. Confirm **source enum** = `ai_accepted | ai_edited | human | unanswered` (overwrite docs/02 §6 wording).
2. Confirm **one AI call per photo** (not grouped upstream+downstream in one request).
3. Confirm **GPS flag distance = 500 m** and the risk High/Moderate heuristics above, or supply preferred numbers.
4. Confirm feelings **1–5** until official range known.
5. Any must-have from nice-to-haves (CSV, Bengali/Hindi) before cut line?

---

## Next step

Stop here. After you approve or amend this plan (especially §6 open questions), run **Prompt 1 — Scaffold** from `_my_notes/prompts.md`.
