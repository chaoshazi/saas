"""Storage factory and exports."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> StorageBackend:
    backend = settings.storage_backend.lower()
    if backend == "local":
        return LocalStorage()
    if backend in {"s3", "oss", "minio"}:
        # Reserved for the S3/OSS/MinIO adapter; V1 defaults to local.
        raise NotImplementedError(f"storage backend {backend!r} is not configured; use 'local'")
    raise ValueError(f"unknown storage backend: {backend}")


__all__ = ["StorageBackend", "LocalStorage", "get_storage"]
