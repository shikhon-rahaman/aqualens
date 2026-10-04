# Decisions log
1. **Track:** Track 3 (AI-Supported Assessment) primary; Track 7 (FHIR) and light Track 2/6 insight as extras.
2. **Cost:** zero. Free tiers and open source only.
3. **AI provider:** Groq vision model only, behind an adapter with fallbacks: groq -> cache (previous results) -> mock. Decision to keep Groq-only is conditional on passing the Day-1 photo test (scripts/groq_photo_test.py).
4. **Human in the loop:** AI suggests, human confirms. Human-only fields: water height, feelings, overall assessment (chosen before the AI comparison is shown).
5. **Form fidelity:** mirror the official app's questions and answer codes (docs/02).
6. **Fields still unconfirmed:** habitats, debris, water height unit. Build them as simple presence-only fields / plain number until confirmed.
7. **Data:** demo sites and seeded observations are synthetic, flagged is_synthetic, shown as "Demo data".
8. **Expert access:** a simple PIN, demo-only; real authentication is future work.
9. **FHIR:** transaction Bundle (Location, Observations, Provenance) sent only to a public test server, without photos, free text or feelings.
10. **Platform:** mobile-first PWA, matching how the official app is used.
