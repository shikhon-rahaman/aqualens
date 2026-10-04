# Notes on the official OneAquaHealth Citizen Science App (v1.0)

## How it works
- It is a PWA at apps.oneaquahealth.eu/citizens. Users install it with "Add to Home Screen" (iOS share icon, Android menu). Citizens must first join the OneAquaHealth Community and log in with an assigned email and password.
- Sidebar: Make new Observation, My Submissions, Instructions.
- A 9-step wizard:
  1. Basic Information (what the app is for, "Before you submit").
  2. Additional Details: choose an official site from a long list (codes like "C3 / Vale das Flores") plus a Mapbox map with pins, or "Add New Site". Coordinates come from the chosen site.
  3. Media Upload: upstream photo, downstream photo, photo of the surrounding context (houses, roads), photo of an interesting element of biodiversity, short 5–10 s video.
  4. Questions (1/3): channel form, bottom type, bank type, habitats, natural debris, water flow.
  5. Questions (2/3): water aspect, water withdrawal, barriers, draining pipes, sewage discharge, construction, water height.
  6. Questions (3/3): margin (5–10 m from top of bank) impervious areas left/right, vegetation left/right and type, invasive species, vegetation cuts. Left and right are defined looking downstream.
  7. Feedback (1/2): overall ecosystem assessment: Good / Moderate / Poor.
  8. Feedback (2/2): feelings sliders (Joy, Serenity, Anger, Fear) with Not applicable, default 3.
  9. Review: summary cards of all answers, then submit.
- Most questions are multiple choice with reference pictures labelled A/B/C/D and an "I'm not sure" option.

## Weaknesses AquaLens addresses (UX and data-quality gaps)
- Distance to sites shows "NaNkm" when location is off; choosing from a long list of codes is confusing.
- Citizens must match cartoon or reference pictures to a real stream; many answers will be "not sure" or wrong.
- Nothing checks the answers for contradictions (for example dry flow but a water height, or "Good" overall with concrete banks and a pipe).
- Left vs right bank is easy to mix up.
- Review card names differ from question titles (Water Quality, Water Abstraction, Water Extraction vs Water Aspect, Water Withdrawal, Sewage discharge).

## Not confirmed yet (PENDING)
- Meaning of Habitats letters A–E and Natural debris letters A–C (info popups not captured).
- Unit of Water height.
- Range of feelings sliders.
- Whether the app has an API or data export (ask in the hackathon Slack).

## Rules for using this material
- Do not copy the app's reference images or long texts into the repo or demo. Write original help text and use own illustrations.
- Do not submit fake observations into the real app.
