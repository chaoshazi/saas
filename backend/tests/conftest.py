"""Test fixtures and environment."""
from __future__ import annotations

import os
import pathlib

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_saas.db"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef-0123456789abcdef"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/0"
os.environ["CORS_ORIGINS"] = '["http://test"]'
os.environ["STORAGE_LOCAL_ROOT"] = "./test_uploads"
os.environ["RATE_LIMIT_REQUESTS"] = "100000"

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
DB_FILE = BACKEND_DIR / "test_saas.db"
UPLOAD_DIR = BACKEND_DIR / "test_uploads"


@pytest.fixture(autouse=True)
def _clean_db_files():
    if DB_FILE.is_file():
        DB_FILE.unlink()
    if UPLOAD_DIR.is_dir():
        import shutil

        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    yield


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def unique() -> str:
    import uuid

    return uuid.uuid4().hex[:10]

