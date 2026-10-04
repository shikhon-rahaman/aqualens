"""Seed script: 25 synthetic observations with realistic variety.

Creates observations across demo sites with:
- Mix of risk levels (good/moderate/poor)
- Some flagged for expert review
- Varied field sources (AI accepted, edited, human-only)
- Pre-warmed AI cache entries for demo photos
- Realistic timestamps spread over last 30 days

Usage:
    python scripts/seed.py
"""

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.models import Observation, Site
from app.seed import seed_demo_sites

# Realistic answer patterns
ANSWER_TEMPLATES = [
    # Good condition
    {
        "water_flow": "steady",
        "water_aspect": "clear",
        "water_smell": "absent",
        "algae": "absent",
        "litter": "absent",
        "sewage": "absent",
        "invasive_plants": "absent",
        "clarity": "high",
        "overall_assessment": "good",
    },
    # Moderate with some pressures
    {
        "water_flow": "steady",
        "water_aspect": "cloudy",
        "water_smell": "mild",
        "algae": "some",
        "litter": "some",
        "sewage": "absent",
        "invasive_plants": "some",
        "clarity": "medium",
        "overall_assessment": "moderate",
    },
    # Poor condition
    {
        "water_flow": "trickle",
        "water_aspect": "murky",
        "water_smell": "strong",
        "algae": "abundant",
        "litter": "abundant",
        "sewage": "present",
        "invasive_plants": "abundant",
        "clarity": "low",
        "overall_assessment": "poor",
    },
    # Mixed signals (will trigger flags)
    {
        "water_flow": "steady",
        "water_aspect": "clear",
        "water_smell": "absent",
        "algae": "abundant",  # Conflict!
        "litter": "absent",
        "sewage": "absent",
        "invasive_plants": "some",
        "clarity": "high",
        "overall_assessment": "good",  # Mismatch with algae
    },
]

FEELINGS_TEMPLATES = [
    {"joy": 4, "serenity": 5, "anger": 1, "fear": 1},  # Peaceful site
    {"joy": 3, "serenity": 3, "anger": 2, "fear": 2},  # Neutral
    {"joy": 2, "serenity": 2, "anger": 4, "fear": 3},  # Concerning site
    {"joy": 3, "serenity": 4, "anger": 1, "fear": 1},  # Pleasant
]


def create_field_sources(answers: dict, ai_ratio: float = 0.7) -> dict:
    """Generate realistic field sources."""
    sources = {}
    for field_id in answers.keys():
        if field_id == "overall_assessment":
            sources[field_id] = "human"
        elif random.random() < ai_ratio:
            if random.random() < 0.8:
                sources[field_id] = "ai_accepted"
            else:
                sources[field_id] = "ai_edited"
        else:
            sources[field_id] = "human"
    return sources


def create_ai_suggestions(answers: dict) -> dict:
    """Generate AI suggestions that may or may not match answers."""
    suggestions = {}
    for field_id, value in answers.items():
        if field_id == "overall_assessment":
            continue  # Human-only
        # 80% chance AI suggestion matches, 20% differs
        if random.random() < 0.8:
            suggestions[field_id] = {
                "value": value,
                "confidence": random.uniform(0.7, 0.95),
                "reason": f"Pattern analysis suggests {value}",
            }
        else:
            # AI got it wrong
            alt_values = ["absent", "some", "abundant"]
            alt_value = random.choice([v for v in alt_values if v != value])
            suggestions[field_id] = {
                "value": alt_value,
                "confidence": random.uniform(0.5, 0.7),
                "reason": f"Visual indicators suggest {alt_value}",
            }
    return suggestions


def create_feelings(template: dict) -> dict:
    """Create feelings with slight variations."""
    return {
        key: {"value": val + random.randint(-1, 1), "na": False}
        for key, val in template.items()
    }


def evaluate_synthetic(answers: dict) -> dict:
    """Simple evaluation for synthetic data."""
    overall = answers.get("overall_assessment", "moderate")

    # Count pressure signals
    pressures = 0
    if answers.get("algae") in ["some", "abundant"]:
        pressures += 1
    if answers.get("litter") in ["some", "abundant"]:
        pressures += 1
    if answers.get("sewage") == "present":
        pressures += 2
    if answers.get("invasive_plants") in ["some", "abundant"]:
        pressures += 1
    if answers.get("water_aspect") in ["cloudy", "murky"]:
        pressures += 1

    # Determine suggested level
    if pressures >= 4:
        suggested = "poor"
    elif pressures >= 2:
        suggested = "moderate"
    else:
        suggested = "good"

    # Check for mismatch
    levels = ["good", "moderate", "poor"]
    user_idx = levels.index(overall) if overall in levels else 1
    suggested_idx = levels.index(suggested)
    mismatch = abs(user_idx - suggested_idx)

    needs_expert = mismatch >= 2 or pressures >= 3

    # Generate flags
    flags = []
    if answers.get("algae") == "abundant" and answers.get("clarity") == "high":
        flags.append({
            "code": "clarity_algae_conflict",
            "fields": ["algae", "clarity"],
            "message": "High clarity but abundant algae reported - please verify",
            "severity": "warning",
            "needs_expert": True,
        })

    if answers.get("water_smell") == "strong" and answers.get("sewage") == "absent":
        flags.append({
            "code": "smell_without_sewage",
            "fields": ["water_smell", "sewage"],
            "message": "Strong smell but no sewage - check for other sources",
            "severity": "info",
            "needs_expert": False,
        })

    # Risk assessment
    contact_level = "poor" if answers.get("sewage") == "present" else "good"
    ecosystem_level = suggested

    return {
        "overall_suggested": suggested,
        "needs_expert": needs_expert or len([f for f in flags if f["needs_expert"]]) > 0,
        "flags": flags,
        "risk_contact": contact_level,
        "risk_ecosystem": ecosystem_level,
        "risk_reasons": {
            "contact": ["Sewage detected"] if contact_level == "poor" else [],
            "ecosystem": [f"{pressures} pressure signals detected"],
            "disclaimer": "Indicative only, not a safety certification",
        },
    }


def seed_observations(count: int = 25):
    """Seed realistic synthetic observations."""
    settings = get_settings()
    init_db()
    db = SessionLocal()

    try:
        # Ensure demo sites exist
        seed_demo_sites(db)
        sites = list(db.query(Site).filter(Site.is_demo == True).all())

        if not sites:
            print("No demo sites found!")
            return

        print(f"Seeding {count} synthetic observations across {len(sites)} sites...")

        created = 0
        for i in range(count):
            site = random.choice(sites)
            template = random.choice(ANSWER_TEMPLATES)
            feelings_template = random.choice(FEELINGS_TEMPLATES)

            # Create answers with slight variations
            answers = dict(template)

            # Random timestamp in last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            captured_at = datetime.now(timezone.utc) - timedelta(
                days=days_ago, hours=hours_ago
            )

            # Generate related data
            field_sources = create_field_sources(answers)
            ai_suggestions = create_ai_suggestions(answers)
            feelings = create_feelings(feelings_template)
            eval_result = evaluate_synthetic(answers)

            # Facing downstream (mostly yes)
            facing_downstream = random.random() > 0.2

            # Create observation
            obs = Observation(
                site_id=site.id,
                user_lat=site.lat + random.uniform(-0.001, 0.001),
                user_lon=site.lon + random.uniform(-0.001, 0.001),
                facing_downstream=facing_downstream,
                captured_at=captured_at,
                photos_json={},  # No actual photos for synthetic data
                answers_json=answers,
                ai_suggestions_json=ai_suggestions,
                field_sources_json=field_sources,
                flags_json=eval_result["flags"],
                needs_expert=eval_result["needs_expert"],
                status="confirmed",
                overall_user=answers["overall_assessment"],
                overall_suggested=eval_result["overall_suggested"],
                risk_contact=eval_result["risk_contact"],
                risk_ecosystem=eval_result["risk_ecosystem"],
                risk_reasons_json=eval_result["risk_reasons"],
                feelings_json=feelings,
                is_synthetic=True,
            )

            db.add(obs)
            created += 1

            if created % 5 == 0:
                print(f"  Created {created}/{count}...")

        db.commit()
        print(f"[+] Successfully created {created} synthetic observations")

        # Summary stats
        needs_review = db.query(Observation).filter(
            Observation.is_synthetic == True,
            Observation.needs_expert == True
        ).count()

        print(f"\nSummary:")
        print(f"  Total synthetic observations: {created}")
        print(f"  Needing expert review: {needs_review}")
        print(f"  Distribution across {len(sites)} demo sites")

    except Exception as e:
        db.rollback()
        print(f"[X] Error seeding observations: {e}")
        raise
    finally:
        db.close()


def warm_ai_cache():
    """Pre-warm AI cache with common demo photo responses."""
    settings = get_settings()
    cache_dir = Path(settings.ai_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    print("\nWarming AI cache with demo responses...")

    # Common demo responses
    demo_responses = [
        {
            "suggestions": {
                "water_flow": {
                    "value": "steady",
                    "confidence": 0.85,
                    "reason": "Water shows consistent flow patterns",
                },
                "water_aspect": {
                    "value": "clear",
                    "confidence": 0.9,
                    "reason": "Water appears transparent",
                },
                "algae": {
                    "value": "absent",
                    "confidence": 0.8,
                    "reason": "No visible algae growth",
                },
            },
            "status": "ok",
        },
        {
            "suggestions": {
                "water_flow": {
                    "value": "steady",
                    "confidence": 0.75,
                    "reason": "Moderate flow visible",
                },
                "water_aspect": {
                    "value": "cloudy",
                    "confidence": 0.85,
                    "reason": "Water shows turbidity",
                },
                "algae": {
                    "value": "some",
                    "confidence": 0.7,
                    "reason": "Patches of algae visible",
                },
            },
            "status": "ok",
        },
    ]

    for i, response in enumerate(demo_responses):
        cache_file = cache_dir / f"demo_cache_{i}.json"
        with open(cache_file, "w") as f:
            json.dump(response, f, indent=2)
        print(f"  [+] Created cache entry: {cache_file.name}")

    print(f"[+] AI cache warmed with {len(demo_responses)} entries")


if __name__ == "__main__":
    print("=" * 60)
    print("AquaLens Synthetic Data Seeder")
    print("=" * 60)

    seed_observations(25)
    warm_ai_cache()

    print("\n" + "=" * 60)
    print("Seeding complete! Run the app and check:")
    print("  - Map page should show 25+ pins")
    print("  - Expert queue should have observations pending review")
    print("  - All observations marked as 'Demo data'")
    print("=" * 60)
