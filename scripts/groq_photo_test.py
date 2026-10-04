"""
AquaLens Day-1 test: send stream photos to Groq's vision model and check
JSON validity, speed, token use and agreement with YOUR own labels.

Setup (Windows, in your project folder):
    pip install groq python-dotenv pillow
    Create a folder  test_photos/  and put 10-15 .jpg/.jpeg/.png photos in it.
    Create a file  .env  (and add .env to .gitignore!) containing:
        GROQ_API_KEY=your_key_here
        GROQ_VISION_MODEL=<copy the current vision model id from console.groq.com/docs/vision>
        SLEEP_SECONDS=30
    Optional: labels.csv with columns
        filename,water_aspect,bank_type,bottom_type,draining_pipes,water_flow
    (use the app codes: A/B/C/D, yes/no, not_sure)

Run:  python groq_photo_test.py
Output: results.csv and a summary printed at the end.
"""
import base64
import csv
import io
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from PIL import Image

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_VISION_MODEL")
SLEEP = float(os.getenv("SLEEP_SECONDS", "30"))
PHOTO_DIR = Path("test_photos")
LABELS_FILE = Path("labels.csv")
CONF_THRESHOLD = 0.7

if not API_KEY or not MODEL:
    raise SystemExit("Set GROQ_API_KEY and GROQ_VISION_MODEL in your .env file first.")

client = Groq(api_key=API_KEY)

SYSTEM_PROMPT = """You help citizens assess urban streams from ONE photo.
Rules:
- Answer only what is clearly visible. If unsure, use "not_sure". Never guess.
- Give confidence 0 to 1 and ONE short sentence as reason.
- Flow (A/B/C) and channel_form cannot be judged reliably from a still photo: keep confidence at 0.6 or below unless clearly dry.
- For draining_pipes, sewage_discharge, construction: describe only what is visible. Never accuse or state a cause.
- Output JSON only. No markdown, no extra text.
Return exactly these keys, each as {"value": ..., "confidence": 0.0, "reason": ""}:
water_aspect: A clear | B muddy_turbid | C foam | D altered_colour | not_sure
water_flow: A fast | B slow | C stagnant_or_intermittent | D dry | not_sure
bottom_type: A natural | B artificial | not_sure
bank_type: A natural | B artificial | C laid_stones_no_concrete | not_sure
channel_form: A flat | B u_shape | C v_shape | not_sure
barriers: yes | no | not_sure
draining_pipes: yes | no | not_sure
sewage_discharge: yes | no | not_sure
construction: yes | no | not_sure
habitats_present: yes | no | not_sure
natural_debris_present: yes | no | not_sure
Use the letter (A/B/C/D) or yes/no/not_sure as the value.
Also include "image_quality": {"usable": true, "issue": ""}."""

FIELDS = [
    "water_aspect", "water_flow", "bottom_type", "bank_type", "channel_form",
    "barriers", "draining_pipes", "sewage_discharge", "construction",
    "habitats_present", "natural_debris_present",
]


def encode_image(path: Path, max_side: int = 1024) -> str:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def parse_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def call_model(b64: str):
    return client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Assess this stream photo."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ],
    )


def analyse(path: Path):
    b64 = encode_image(path)
    start = time.time()
    for attempt in range(2):  # one retry on rate limit / bad JSON
        try:
            resp = call_model(b64)
            data = parse_json(resp.choices[0].message.content)
            return {
                "ok": True,
                "data": data,
                "seconds": round(time.time() - start, 1),
                "tokens": getattr(resp.usage, "total_tokens", None),
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001 - test script, report everything
            err = str(exc)[:200]
            if attempt == 0:
                time.sleep(SLEEP)
                continue
            return {"ok": False, "data": {}, "seconds": round(time.time() - start, 1),
                    "tokens": None, "error": err}


def load_labels():
    if not LABELS_FILE.exists():
        return {}
    with LABELS_FILE.open(newline="", encoding="utf-8") as f:
        return {row["filename"]: row for row in csv.DictReader(f)}


def main():
    photos = sorted(p for p in PHOTO_DIR.iterdir()
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not photos:
        raise SystemExit("Put photos in the test_photos/ folder first.")
    labels = load_labels()

    rows, valid = [], 0
    agree = {f: [0, 0] for f in FIELDS}  # [matches, compared] for confident answers
    abstain = {f: 0 for f in FIELDS}

    for i, p in enumerate(photos, 1):
        print(f"[{i}/{len(photos)}] {p.name} ...", flush=True)
        r = analyse(p)
        valid += r["ok"]
        row = {"filename": p.name, "valid_json": r["ok"], "seconds": r["seconds"],
               "tokens": r["tokens"], "error": r["error"]}
        for f in FIELDS:
            item = r["data"].get(f, {}) if isinstance(r["data"], dict) else {}
            val, conf = item.get("value", ""), item.get("confidence", "")
            row[f] = val
            row[f + "_conf"] = conf
            row[f + "_reason"] = item.get("reason", "")
            try:
                conf_f = float(conf)
            except (TypeError, ValueError):
                conf_f = 0.0
            if val == "not_sure" or conf_f < CONF_THRESHOLD:
                abstain[f] += 1
            elif p.name in labels and labels[p.name].get(f):
                agree[f][1] += 1
                agree[f][0] += str(val).strip().lower() == labels[p.name][f].strip().lower()
        rows.append(row)
        if i < len(photos):
            time.sleep(SLEEP)  # stay under the free tokens-per-minute limit

    with open("results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\n=== SUMMARY ===")
    print(f"Valid JSON: {valid}/{len(photos)} ({100 * valid / len(photos):.0f}%)")
    toks = [r["tokens"] for r in rows if r["tokens"]]
    if toks:
        print(f"Tokens per call: avg {sum(toks) / len(toks):.0f}, max {max(toks)}")
    secs = [r["seconds"] for r in rows]
    print(f"Seconds per call: avg {sum(secs) / len(secs):.1f}")
    if labels:
        print(f"\nAgreement with your labels (only answers with confidence >= {CONF_THRESHOLD}):")
        for f in FIELDS:
            m, c = agree[f]
            if c:
                print(f"  {f}: {m}/{c} ({100 * m / c:.0f}%)  | abstained on {abstain[f]} photos")
    print("\nOpen results.csv and check the 'reason' columns, especially the blurry photo,")
    print("the photos with no pipe (must not say yes), and the flow answers.")


if __name__ == "__main__":
    main()
