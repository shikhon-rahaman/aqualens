"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.routers import analyze, form_schema, health, observations, sites
from app.seed import seed_demo_sites


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    db = SessionLocal()
    try:
        seed_demo_sites(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AquaLens API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(form_schema.router)
    app.include_router(sites.router)
    app.include_router(observations.router)
    app.include_router(analyze.router)

    upload_root = Path(settings.upload_dir)
    if not upload_root.is_absolute():
        upload_root = Path.cwd() / upload_root
    upload_root.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_root)), name="uploads")
    return app


app = create_app()
