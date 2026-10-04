"""Storage adapter and observation photo tests."""

import io
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base as ExifBase

from app.adapters.storage import LocalStorageAdapter, resize_and_strip_exif
from app.config import get_settings


def _make_jpeg_bytes(width: int, height: int, *, with_exif: bool = False) -> bytes:
    img = Image.new("RGB", (width, height), color=(30, 120, 180))
    buf = io.BytesIO()
    if with_exif:
        exif = img.getexif()
        exif[ExifBase.Make] = "AquaLensTestCam"
        exif[ExifBase.Model] = "UnitTest"
        img.save(buf, format="JPEG", quality=90, exif=exif)
    else:
        img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_resize_long_edge_to_1024():
    raw = _make_jpeg_bytes(2048, 1024)
    out = resize_and_strip_exif(raw)
    with Image.open(io.BytesIO(out)) as img:
        assert max(img.size) == 1024
        assert img.format == "JPEG"


def test_strip_exif():
    raw = _make_jpeg_bytes(800, 600, with_exif=True)
    with Image.open(io.BytesIO(raw)) as original:
        assert original.getexif().get(ExifBase.Make) == "AquaLensTestCam"
    out = resize_and_strip_exif(raw)
    with Image.open(io.BytesIO(out)) as cleaned:
        assert cleaned.getexif().get(ExifBase.Make) is None


def test_local_storage_writes_under_observation_folder(tmp_path: Path):
    adapter = LocalStorageAdapter(root=tmp_path / "uploads")
    raw = _make_jpeg_bytes(1600, 900)
    key = adapter.save_photo("obs-123", "upstream", raw)
    assert key == "/uploads/obs-123/upstream.jpg"
    path = tmp_path / "uploads" / "obs-123" / "upstream.jpg"
    assert path.exists()
    with Image.open(path) as img:
        assert max(img.size) <= 1024


def test_create_observation_with_photo(client, upload_dir: Path):
    sites = client.get("/api/sites").json()["sites"]
    site_id = sites[0]["id"]
    raw = _make_jpeg_bytes(1200, 800, with_exif=True)

    response = client.post(
        "/api/observations",
        data={
            "site_id": site_id,
            "facing_downstream": "true",
            "answers": '{"water_aspect":"A","overall_assessment":"good"}',
            "field_sources": '{"water_aspect":"human","overall_assessment":"human"}',
        },
        files={
            "photo_upstream": ("up.jpg", raw, "image/jpeg"),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["site_id"] == site_id
    assert "upstream" in body["photos"]
    assert body["field_sources"]["water_aspect"] == "human"
    assert body["answers"]["water_aspect"] == "A"

    # File landed in configured upload dir
    saved = list(upload_dir.rglob("upstream.jpg"))
    assert len(saved) == 1
    with Image.open(saved[0]) as img:
        assert img.getexif().get(ExifBase.Make) is None


def test_create_observation_json_and_list(client):
    sites = client.get("/api/sites").json()["sites"]
    site_id = sites[0]["id"]
    created = client.post(
        "/api/observations/json",
        json={
            "site_id": site_id,
            "facing_downstream": True,
            "answers": {"water_flow": "D", "water_height": 0},
            "field_sources": {"water_flow": "ai_accepted", "water_height": "human"},
            "is_synthetic": True,
            "status": "confirmed",
        },
    )
    assert created.status_code == 201, created.text
    obs_id = created.json()["id"]

    listed = client.get("/api/observations")
    assert listed.status_code == 200
    ids = {o["id"] for o in listed.json()["observations"]}
    assert obs_id in ids

    detail = client.get(f"/api/observations/{obs_id}")
    assert detail.status_code == 200
    assert detail.json()["is_synthetic"] is True
    assert detail.json()["field_sources"]["water_flow"] == "ai_accepted"


def test_reject_invalid_answers(client):
    sites = client.get("/api/sites").json()["sites"]
    site_id = sites[0]["id"]
    response = client.post(
        "/api/observations/json",
        json={
            "site_id": site_id,
            "answers": {"water_aspect": "not-a-code"},
        },
    )
    assert response.status_code == 422


def test_get_settings_storage_defaults():
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.storage_backend in {"local", "supabase"}
