"""Pytest fixtures for the AquaLens backend."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import Base, get_db
from app.main import create_app
from app.seed import seed_demo_sites


@pytest.fixture()
def upload_dir(tmp_path: Path) -> Path:
    path = tmp_path / "uploads"
    path.mkdir()
    return path


@pytest.fixture()
def client(tmp_path: Path, upload_dir: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("AI_PROVIDER_CHAIN", "mock")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "ai_cache"))
    monkeypatch.setenv("SLEEP_SECONDS", "0")
    get_settings.cache_clear()

    db = TestingSessionLocal()
    try:
        seed_demo_sites(db)
    finally:
        db.close()

    app = create_app()

    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture()
def db_session(tmp_path: Path):
    db_path = tmp_path / "unit.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
