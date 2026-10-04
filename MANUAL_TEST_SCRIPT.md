# Manual Test Script - Result, Map, Expert Pages & Feelings Chart

Date: 2026-09-20

## Prerequisites
- Backend running: `cd backend && .venv/Scripts/activate && uvicorn app.main:app --reload`
- Frontend running: `cd frontend && npm run dev`
- At least one observation saved (complete the citizen flow first)
- EXPERT_PIN configured in `.env` (default: `change-me`)

---

## Test 1: Result Page Enhancements

### Setup
1. Complete a citizen observation (site → photos → analyze → review → overall → feelings → final)
2. Note the observation ID from the URL `/result/{id}`

### Risk Notes with Reasons
- [ ] "Risk notes" section shows Contact safety level
- [ ] Contact safety reasons listed as bullets (if any)
- [ ] Ecosystem pressure level shown
- [ ] Ecosystem pressure reasons listed as bullets (if any)
- [ ] Disclaimer text: "Indicative only, not a safety certification"

### Flags Display
- [ ] If observation has validation flags, they appear in amber boxes
- [ ] Each flag shows its plain-language message
- [ ] No flags section if observation has no flags

### Source Badges Section
- [ ] "Source badges" section appears
- [ ] Explains that sources are shown in details

### FHIR Export
- [ ] "FHIR Export" section with two buttons
- [ ] "View FHIR" button loads JSON viewer
- [ ] Click "View FHIR" → details element expands
- [ ] Shows "FHIR JSON (N resources)" summary
- [ ] JSON is formatted with 2-space indent
- [ ] "Send to FHIR test server" button enabled
- [ ] Click "Send to FHIR test server"
  - Button shows "Sending…" and becomes disabled
  - Success: green box with "✓ Sent successfully", HTTP status, timestamp
  - Shows excluded fields (photos, feelings, etc.)
  - Server response in collapsible details
- [ ] Error handling: red box with error message if send fails

### Feelings Chart
- [ ] "Average feelings at this site" chart appears
- [ ] Four bars: Joy (green), Serenity (blue), Anger (red), Fear (purple)
- [ ] Each bar shows label, value (e.g., "3.2 / 5"), and colored progress bar
- [ ] Sample count shown (e.g., "n=12")
- [ ] Warning: "⚠ Demo data. Association only, not proof of cause..."

### Navigation
- [ ] "New observation" button → `/observe`
- [ ] "View on map" button → `/map`

---

## Test 2: Map Page

### Initial Load
- [ ] Map loads with OpenStreetMap tiles
- [ ] Shows "N observations shown" count
- [ ] If demo data exists, badge shows "Demo data included"

### Markers
- [ ] Observations appear as colored map pins
- [ ] Pin colors match risk level:
  - Green = good
  - Yellow = moderate
  - Red = poor
  - Gray = no risk data
- [ ] Clicking a pin opens a popup

### Popup Content
- [ ] Site name as header
- [ ] Risk level: "Risk: [level]"
- [ ] Citizen rating if available: "Citizen rating: [rating]"
- [ ] Amber badge if needs expert review: "Needs expert review"
- [ ] "Demo data" label if synthetic
- [ ] "View details" button links to `/result/{id}`

### Filters
- [ ] "Needs review only" checkbox
  - Check it → only observations with needs_expert=true shown
  - Uncheck → all shown again
- [ ] Risk level radio buttons: All risks, Good, Moderate, Poor
  - Select "Good" → only green pins shown
  - Select "Moderate" → only yellow pins shown
  - Select "Poor" → only red pins shown
  - Select "All risks" → all pins shown

### Map Interaction
- [ ] Zoom in/out with mouse wheel or zoom controls
- [ ] Pan by dragging
- [ ] Markers stay clickable at all zoom levels

### No Data Case
- [ ] If no observations with coordinates, map still loads
- [ ] Default center: [51.505, -0.09] (London)

### Navigation
- [ ] "New observation" button at bottom

---

## Test 3: Expert Page - Authentication

### PIN Prompt
- [ ] Page shows "Expert review" header
- [ ] Text: "Enter PIN to access the review queue."
- [ ] Amber warning box: "⚠ Demo-only authentication. Real auth is future work."
- [ ] Password input field with placeholder "Enter PIN from .env"
- [ ] "Access queue" button

### Authentication Flow
- [ ] Leave PIN empty, click "Access queue" → error: "PIN required"
- [ ] Enter wrong PIN → error: "Invalid or missing expert PIN" (401)
- [ ] Enter correct PIN from .env (default: `change-me`)
  - Button shows "Authenticating…"
  - Success → queue list appears

### Keyboard Interaction
- [ ] Type PIN and press Enter → submits (same as clicking button)

---

## Test 4: Expert Page - Queue List

### Queue Display
- [ ] Header: "Expert queue"
- [ ] Count: "N observations need review"
- [ ] If no observations need review: "No observations pending review." in gray box

### Queue Items
For each observation in queue:
- [ ] White card with border
- [ ] Site name as header (or "Unknown site")
- [ ] Line: "User rating: [rating] · AI: [level]"
- [ ] Timestamp: formatted date/time
- [ ] If synthetic: " · Demo data" suffix
- [ ] Hovering card → border changes to brand-300
- [ ] Clicking card → loads detail view

### Sign Out
- [ ] "Sign out" link at bottom
- [ ] Click → returns to PIN prompt, clears queue

---

## Test 5: Expert Page - Detail View

### Navigation
- [ ] "← Back to queue" link returns to queue list
- [ ] Header: "Review observation"
- [ ] Site name and status displayed

### Photos Section
- [ ] "Photos" section appears if observation has photos
- [ ] 2-column grid of photos
- [ ] Each photo: image with aspect-video ratio, caption (upstream, downstream, context, biodiversity)
- [ ] Photos load from backend `/uploads/` path
- [ ] If no photos, section not shown

### Flags Section
- [ ] If observation has flags, "Flags" section shown
- [ ] Each flag in amber box with message
- [ ] If no flags, section not shown

### Answers Section
- [ ] "Answers" section with "Edit" link in header
- [ ] All answered fields listed
- [ ] Each field: question, value (with label), source badge
- [ ] Source badges: "ai accepted", "ai edited", "human", etc.

### Approve Flow
- [ ] "Approve" button (green background)
- [ ] Click "Approve"
  - Button shows "Processing…", becomes disabled
  - Success: returns to queue list, observation removed
  - Status updated to "expert_approved"
  - needs_expert set to false

### Correct Flow - Editing
- [ ] Click "Edit" link in header OR "Correct" button
- [ ] Answers section enters edit mode
- [ ] Each field shows appropriate input:
  - Choice fields: buttons for each option, selected one highlighted
  - Number fields: number input
  - Text fields: textarea
- [ ] Change 2-3 field values
- [ ] "Cancel" button returns to view mode, reverts changes
- [ ] "Save corrections" button at bottom

### Correct Flow - Saving
- [ ] After editing, click "Save corrections"
- [ ] Button shows "Saving…", becomes disabled
- [ ] Backend re-evaluates with new answers
- [ ] Success: returns to queue list
- [ ] Observation status updated to "expert_corrected"
- [ ] If errors resolved, needs_expert may become false

### Error Handling
- [ ] Network error during approve/correct → red error box appears
- [ ] Error message shown: "Review action failed" or specific error

---

## Test 6: Integration - Map Updates After Expert Review

### Setup
1. Note an observation on the map that needs review (amber badge in popup)
2. Go to `/expert`, authenticate, review that observation

### Expected Behavior
- [ ] Refresh map page
- [ ] Observation popup no longer shows "Needs expert review" badge
- [ ] Pin color may change if risk level was re-evaluated

---

## Test 7: Backend Expert Endpoints

### Queue Endpoint
```bash
# Windows PowerShell
$headers = @{ "X-Expert-Pin" = "change-me" }
Invoke-RestMethod -Uri "http://localhost:8000/api/queue" -Headers $headers
```
- [ ] Returns JSON with `observations` array
- [ ] Each item has id, site_name, status, needs_expert, risk_ecosystem, overall_user, is_synthetic, captured_at

### Review Endpoint - Approve
```bash
$headers = @{ "X-Expert-Pin" = "change-me" }
$body = @{ action = "approve" }
Invoke-RestMethod -Uri "http://localhost:8000/api/observations/{id}/review" -Method POST -Headers $headers -Body $body
```
- [ ] Returns updated observation
- [ ] status = "expert_approved"
- [ ] needs_expert = false

### Review Endpoint - Correct
```bash
$headers = @{ "X-Expert-Pin" = "change-me" }
$answers = '{"clarity": "high", "algae": "absent"}'
$sources = '{"clarity": "human", "algae": "human"}'
$body = @{ action = "correct"; answers = $answers; field_sources = $sources }
Invoke-RestMethod -Uri "http://localhost:8000/api/observations/{id}/review" -Method POST -Headers $headers -Body $body
```
- [ ] Returns updated observation
- [ ] status = "expert_corrected"
- [ ] answers updated
- [ ] Re-evaluated: flags, needs_expert, overall_suggested, risk levels

### Wrong PIN
```bash
$headers = @{ "X-Expert-Pin" = "wrong-pin" }
Invoke-RestMethod -Uri "http://localhost:8000/api/queue" -Headers $headers
```
- [ ] Returns 401 Unauthorized
- [ ] Error: "Invalid or missing expert PIN"

---

## Test 8: Accessibility

### Keyboard Navigation
- [ ] Tab through all interactive elements in order
- [ ] Enter/Space activates buttons
- [ ] Map zoom controls keyboard accessible

### Screen Reader
- [ ] Headers have proper hierarchy (h1, h2, h3)
- [ ] ARIA labels on map and form controls
- [ ] Error messages announced with role="alert"
- [ ] Loading states announced with aria-live

### Touch Targets
- [ ] All buttons meet 44px min-h-touch
- [ ] Map markers tappable on mobile

---

## Test 9: Mobile Responsive

### Result Page @ 375px width
- [ ] Risk notes stack vertically
- [ ] FHIR buttons wrap if needed
- [ ] Chart bars display full width

### Map Page @ 375px width
- [ ] Filter controls wrap to multiple rows
- [ ] Map container maintains 500px height
- [ ] Popups readable, "View details" button accessible

### Expert Page @ 375px width
- [ ] Queue cards stack properly
- [ ] Photos grid: 2 columns maintained or stack to 1
- [ ] Answer field editing: choice buttons wrap
- [ ] Approve/Correct buttons side-by-side (flex layout)

---

## Test 10: Edge Cases

### No Observations
- [ ] Map page with no observations: shows empty map
- [ ] Expert queue with no pending reviews: gray message box

### Synthetic Data Indicators
- [ ] Demo observations show "Demo data" badge on map
- [ ] Demo observations show "Demo data" in queue list
- [ ] Clearly distinguishable from real observations

### FHIR Send Failure
- [ ] Disconnect from internet or break FHIR_SERVER_URL in .env
- [ ] Try "Send to FHIR test server"
- [ ] Red error box with failure message

### Long Field Values
- [ ] Observation with 500+ character text answer
- [ ] Detail view displays full text without overflow
- [ ] Edit mode textarea handles long text

---

## Performance Checks

- [ ] Map loads and renders 20+ pins in <2s
- [ ] FHIR JSON viewer renders large bundle in <500ms
- [ ] Expert queue list loads in <1s
- [ ] Detail view with 4 photos loads in <2s
- [ ] Feelings chart animates smoothly

---

## README Verification

- [ ] Open `README.md`
- [ ] Section "Expert PIN (demo-only)" exists
- [ ] Explains X-Expert-Pin header
- [ ] States this is demo-only, real auth is future work
- [ ] References EXPERT_PIN environment variable
- [ ] Shows default value: "change-me"

---

## Quick Smoke Test (5 minutes)

If short on time, run this minimal path:

1. **Result page**: View an observation, click "View FHIR", click "Send to FHIR test server", verify feelings chart appears
2. **Map**: Open map, verify pins colored by risk, click one pin, verify popup, filter by "Needs review only"
3. **Expert auth**: Go to `/expert`, enter wrong PIN → error, enter correct PIN → queue loads
4. **Expert review**: Click queue item, verify photos/flags/answers shown, click "Approve" → returns to queue, observation gone
5. **Verify README**: Search for "Expert PIN" section

✓ Core functionality validated.

---

## Sign Off

- [ ] All 10 test sections completed
- [ ] Edge cases handled gracefully
- [ ] Accessibility verified
- [ ] Mobile responsive confirmed
- [ ] Backend endpoints working
- [ ] README updated with PIN note
- [ ] Build succeeds with no errors
- [ ] Lint passes with no errors

**Tested by:** _________________  
**Date:** _________________  
**Notes:** _________________
