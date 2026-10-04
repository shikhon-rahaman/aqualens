# AquaLens — Form Schema, AI Contract & Day-1 Photo Test
Mirrors the official OneAquaHealth Citizen Science App (9-step wizard). Anything marked **PENDING** was not visible in the screenshots and must be confirmed in the app before final build.

## 1. Official wizard structure
| Step | Title | Content |
|---|---|---|
| 1 | Basic Information | Intro / "Before you submit" |
| 2 | Additional Details | Pick an official site from a list + map (or "Add New Site") |
| 3 | Media Upload | Upstream photo, downstream photo, surrounding-context photo, biodiversity photo, 5–10 s video |
| 4 | Questions (1/3) | Channel, bed, banks, habitats, debris, flow |
| 5 | Questions (2/3) | Water aspect, pressures, water height |
| 6 | Questions (3/3) | Margins: impervious areas, vegetation, invasive species, cuts |
| 7 | Feedback (1/2) | Overall assessment: Good / Moderate / Poor |
| 8 | Feedback (2/2) | Feelings sliders |
| 9 | Review | Summary of all answers, then submit |

## 2. Fields and answer codes
Answer codes: `A/B/C/D` as in the app, plus `not_sure`. Yes/No fields: `yes`, `no`, `not_sure`.

| Field id | Question (app wording) | Values | AI role |
|---|---|---|---|
| `site` | Research site (code + name, coordinates come from the site) | site code | Suggest nearest site from GPS |
| `photo_upstream`, `photo_downstream`, `photo_context`, `photo_biodiversity`, `video` | Media | files | Inputs to AI (video skipped in MVP) |
| `channel_form` | Channel form | A flat · B U shape · C V shape · not_sure | Suggest, often not_sure |
| `bottom_type` | Bottom of wet channel | A natural · B artificial (concrete / stones with concrete) · not_sure | Suggest |
| `bank_type` | Banks of the channel | A natural · B artificial · C laid stones no concrete · not_sure | Suggest |
| `habitats_present` (+ types A–E) | Any habitats present? | bool + **PENDING: meaning of A–E** | Suggest presence; types once known |
| `natural_debris_present` (+ types A–C) | Any natural debris present? | bool + **PENDING: meaning of A–C** | Suggest presence; types once known |
| `water_flow` | How is the water flowing | A fast · B slow · C stagnant/intermittent · D dry · not_sure | Suggest (low confidence unless dry) |
| `water_aspect` | How is the water? | A clear · B muddy/turbid · C foam · D colours/altered colour · not_sure | Suggest (strong) |
| `water_withdrawal` | Obvious water collection/use/removal? | yes/no/not_sure | Suggest only if visible |
| `barriers` | Dams / transversal artificial barriers? | yes/no/not_sure | Suggest only if visible |
| `draining_pipes` | Pipes draining polluted water into the stream? | yes/no/not_sure | Suggest cautiously; always expert review if yes |
| `sewage_discharge` | Any water entry or discharge of sewage? | yes/no/not_sure | Suggest cautiously; always expert review if yes |
| `construction` | Construction/works in stream? | yes/no/not_sure | Suggest only if visible; expert review if yes |
| `water_height` | What is the water height? | number, **PENDING: unit** (info popup) | **Human only**; plausibility check |
| `impervious_left`, `impervious_right` | >1/3 of margin covered by roads/sidewalks/buildings | yes/no/not_sure | Suggest, moderate confidence |
| `vegetation_left`, `vegetation_right` | Margin covered by vegetation? | yes/no/not_sure | Suggest |
| `veg_type_left`, `veg_type_right` | Dominant vegetation (>50%, first 5 m) | A herbs · B shrubs · C trees · not_sure | Suggest |
| `invasive_species` (+ free text "Which ones?") | Non-native/invasive plants? | bool + text | Candidates only, low confidence, expert-confirmed |
| `vegetation_cuts` | Recent cuts of bank vegetation? | yes/no/not_sure | Usually not_sure |
| `overall_assessment` | Overall ecosystem health | good · moderate · poor | **User chooses first**, then comparison shown |
| `feelings` | Joy, Serenity, Anger, Fear | slider (default 3) + "Not applicable" each; **PENDING: range** | **Human only, no AI** |

Left/right are defined **looking downstream**. Notes: the review page card names ("Water Quality", "Water Abstraction", "Water Extraction") differ from the question titles; use the question titles above and confirm the mapping.

## 3. AI output contract (JSON only)
One request per photo group to keep tokens low. Every field returns the same shape:
```json
{
  "field_id": {"value": "A|B|C|D|yes|no|not_sure", "confidence": 0.0, "reason": "one short sentence about what is visible"}
}
```
Rules for the prompt:
- Answer **only what is visible**; use `not_sure` instead of guessing.
- Confidence 0–1; never above 0.6 for flow (A/B/C) or channel_form from a single still photo.
- For `draining_pipes`, `sewage_discharge`, `construction`: describe what is visible ("a pipe is visible on the left bank"), never accuse, never state a cause.
- For vegetation/impervious margins, report **left/right as seen in the image**; the app maps them to stream-left/right only after the user confirms the photo was taken facing downstream.
- No safety advice, no species certainty; invasive species = "possible candidates" only.
- Output JSON only, no markdown fences.

Group A (upstream + downstream photos): `water_aspect`, `water_flow`, `bottom_type`, `bank_type`, `channel_form`, `barriers`, `draining_pipes`, `sewage_discharge`, `water_withdrawal`, `habitats_present`, `natural_debris_present`, plus an `upstream_vs_downstream` note (clarity/colour change, one sentence).
Group B (context photo): `impervious_*`, `vegetation_*`, `veg_type_*`, `construction`.
Group C (biodiversity photo): `possible_taxon_group` (plant/animal/fungus/other/unsure) with confidence.

## 4. Validation rules
1. `water_flow = D (dry)` and `water_height > 0` → flag contradiction.
2. `sewage_discharge = yes` and `draining_pipes = no` → ask user to recheck.
3. `water_aspect = A (clear)` but AI sees turbidity/foam with confidence ≥ 0.7 → flag.
4. `water_height` outside a plausible range or wrong unit → flag (range **PENDING** the unit).
5. `vegetation_left = no` but a `veg_type_left` is set (same for right) → contradiction; hide type unless yes.
6. AI sees dense trees on a bank but user answered "no vegetation" → flag.
7. `draining_pipes = yes`, `sewage_discharge = yes`, `construction = yes`, `vegetation_cuts = yes`, or `invasive_species` ticked → always send to expert queue.
8. Any AI confidence < 0.5, or unusable photo → flag.
9. User GPS more than a set distance from the chosen site → flag.
10. **Overall assessment consistency:** count pressure signals (artificial bed/bank, impervious margins, no vegetation on a margin, non-clear water, pipe, sewage, barrier, construction, withdrawal, cuts). 0–2 → suggests good, 3–5 → moderate, 6+ → poor. Show the comparison **after** the user picks. If they differ by two levels, flag for review. Thresholds are a starting point; tune on test cases.

## 5. Risk notes (indicative only, never a safety certification)
- **Contact-safety note (people and pets):** water_aspect, draining_pipes, sewage_discharge, water_flow, recent rainfall (Open-Meteo).
- **Ecosystem-pressure note:** impervious margins, missing vegetation, cuts, barriers, construction, artificial bed/banks.
- **Well-being view (optional):** per-site average feelings, shown as an association, not proof of cause.

## 6. Provenance badge on every field
`ai_suggested_human_confirmed` · `human_entered` · `not_answered`. Maps to a FHIR `Provenance` resource.

## 7. Day-1 Groq photo test
**Goal:** decide whether Groq's free vision model is accurate and reliable enough to be your only AI provider.

1. Collect **12 photos**: 3 clear natural, 2 turbid/muddy, 2 foam or coloured water, 2 concrete/artificial channel, 1 with a visible pipe, 1 dry or nearly dry, 1 blurry/unusable. Use your own photos or freely licensed ones (credit them).
2. Write **your own answers** for each photo in a table (`water_aspect`, `bank_type`, `bottom_type`, `draining_pipes`, `water_flow`) as ground truth.
3. Send each photo to the Groq vision model with the prompt rules in section 3. Record: JSON valid? tokens used? seconds? any 429 errors?
4. **Pass criteria (suggested):**
   - JSON parses on at least 95% of calls (after stripping fences and one retry)
   - On fields with confidence ≥ 0.7, agreement with your labels of roughly 80% or better
   - Says `not_sure` (or low confidence) on the blurry photo and on flow from still photos
   - Never confidently claims a pipe or sewage on photos that have none
   - One request fits inside the model's free per-minute token limit
5. If it fails, try another Groq vision model or the fallback provider, and tell me the results.

Tip: resize photos to about 1024 px on the long side before sending. Each image costs roughly 2048 input tokens on Groq, so send at most two photos per request.

## 8. Working assumptions (UNCONFIRMED — do not treat as fact)
These come from guessing at reference pictures, not from the official app's info popups. Confirm them in the app before building on them.
- **Habitats letters A–E (guess):** A/B sand or gravel bars, C rocks in the stream, D riffles, E submerged aquatic plants. **Until confirmed: implement habitats as a simple present / not present answer only.**
- **Natural debris letters A–C (guess):** A fallen logs, B branch or twig accumulations, C leaves. **Until confirmed: presence-only.**
- **Water height unit (guess):** centimetres (the reference photo shows a ruler). **Until confirmed:** show the label "cm (unit to be confirmed)", keep the value as a plain number, and use a soft plausibility warning only (for example below 0 or above 300), stored as a config constant.
- **Feelings sliders:** integers 1–5, default 3, each with "Not applicable" (range not confirmed).
- **Official app API or data export:** unknown. AquaLens is a standalone companion prototype that exports FHIR and CSV; it must not submit into the official app.
