"""Photo storage adapters: local filesystem (dev) and Supabase (production)."""

from __future__ import annotations

import io
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image, ImageOps

from app.config import Settings, get_settings

MAX_LONG_EDGE = 1024
JPEG_QUALITY = 85
PHOTO_ROLES = ("upstream", "downstream", "context", "biodiversity")


def resize_and_strip_exif(image_bytes: bytes) -> bytes:
    """Resize so the long edge is at most 1024 px and re-encode as JPEG (no EXIF)."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        width, height = img.size
        long_edge = max(width, height)
        if long_edge > MAX_LONG_EDGE:
            scale = MAX_LONG_EDGE / long_edge
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return out.getvalue()


class StorageAdapter(ABC):
    @abstractmethod
    def save_photo(self, observation_id: str, role: str, image_bytes: bytes) -> str:
        """Store processed bytes; return a public or relative URL/path key."""

    @abstractmethod
    def resolve_url(self, key: str) -> str:
        """Turn a storage key into a URL the API/frontend can use."""


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, root: Path, public_prefix: str = "/uploads") -> None:
        self.root = root
        self.public_prefix = public_prefix.rstrip("/")
        self.root.mkdir(parents=True, exist_ok=True)

    def save_photo(self, observation_id: str, role: str, image_bytes: bytes) -> str:
        if role not in PHOTO_ROLES:
            raise ValueError(f"invalid photo role: {role}")
        processed = resize_and_strip_exif(image_bytes)
        folder = self.root / observation_id
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{role}.jpg"
        path = folder / filename
        path.write_bytes(processed)
        return f"{self.public_prefix}/{observation_id}/{filename}"

    def resolve_url(self, key: str) -> str:
        return key


class SupabaseStorageAdapter(StorageAdapter):
    """Upload to Supabase Storage when credentials are configured.

    Requires ``supabase`` package only when this backend is selected. Falls back
    to raising a clear error if the SDK or credentials are missing.
    """

    def __init__(
        self,
        url: str,
        key: str,
        bucket: str,
        public_base: str | None = None,
    ) -> None:
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required for supabase storage")
        try:
            from supabase import create_client
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Install the supabase package to use STORAGE_BACKEND=supabase"
            ) from exc
        self._client = create_client(url, key)
        self.bucket = bucket
        self.public_base = (public_base or f"{url.rstrip('/')}/storage/v1/object/public/{bucket}").rstrip("/")

    def save_photo(self, observation_id: str, role: str, image_bytes: bytes) -> str:
        if role not in PHOTO_ROLES:
            raise ValueError(f"invalid photo role: {role}")
        processed = resize_and_strip_exif(image_bytes)
        object_path = f"{observation_id}/{role}.jpg"
        self._client.storage.from_(self.bucket).upload(
            object_path,
            processed,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
        return f"{self.public_base}/{object_path}"

    def resolve_url(self, key: str) -> str:
        return key


def get_storage(settings: Settings | None = None) -> StorageAdapter:
    cfg = settings or get_settings()
    backend = cfg.storage_backend.lower().strip()
    if backend == "supabase":
        return SupabaseStorageAdapter(
            url=cfg.supabase_url,
            key=cfg.supabase_key,
            bucket=cfg.supabase_bucket,
        )
    root = Path(cfg.upload_dir)
    if not root.is_absolute():
        # Resolve relative to backend working directory.
        root = Path.cwd() / root
    return LocalStorageAdapter(root=root)


def new_observation_id() -> str:
    return str(uuid.uuid4())
