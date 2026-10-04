"""Warm the AI cache by running a folder of demo photos through Groq.

Usage (from repo root, with .env configured):

    cd backend
    .\\.venv\\Scripts\\Activate.ps1
    python ..\\scripts\\warm_cache.py --photos ..\\test_photos

Photos are resized, sent one role at a time (upstream by default unless the
filename contains a role hint), and successful Groq results are written under
AI_CACHE_DIR.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.adapters.storage import resize_and_strip_exif  # noqa: E402
from app.ai.cache_provider import CachedProvider  # noqa: E402
from app.ai.groq_provider import GroqProvider  # noqa: E402
from app.config import get_settings  # noqa: E402


ROLE_HINTS = ("upstream", "downstream", "context", "biodiversity")


def guess_role(path: Path, default_role: str) -> str:
    name = path.stem.lower()
    for role in ROLE_HINTS:
        if role in name:
            return role
    return default_role


def main() -> int:
    parser = argparse.ArgumentParser(description="Warm AquaLens AI cache via Groq")
    parser.add_argument(
        "--photos",
        type=Path,
        default=ROOT / "test_photos",
        help="Folder of jpg/png photos",
    )
    parser.add_argument(
        "--default-role",
        default="upstream",
        choices=ROLE_HINTS,
        help="Role when filename has no hint",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.groq_api_key or not settings.groq_vision_model:
        print("Set GROQ_API_KEY and GROQ_VISION_MODEL in .env first.")
        return 1

    folder: Path = args.photos
    if not folder.is_dir():
        print(f"Photo folder not found: {folder}")
        return 1

    cache_dir = Path(settings.ai_cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = (BACKEND / cache_dir).resolve()
    cache = CachedProvider(cache_dir)
    provider = GroqProvider(settings)

    paths = sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not paths:
        print(f"No images in {folder}")
        return 1

    print(f"Warming cache at {cache_dir} with {len(paths)} photos…")
    for index, path in enumerate(paths):
        role = guess_role(path, args.default_role)
        raw = path.read_bytes()
        image = resize_and_strip_exif(raw)
        try:
            result = provider.analyze(image, role)
            cache.put(image, role, result)
            print(f"  OK  {path.name} → role={role} fields={len(result.suggestions)}")
        except Exception as exc:
            print(f"  FAIL {path.name}: {exc}")
        if index < len(paths) - 1 and settings.sleep_seconds > 0:
            time.sleep(settings.sleep_seconds)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
