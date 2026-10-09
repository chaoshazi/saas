"""Local filesystem storage backend."""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.storage_local_root).resolve()

    def _path(self, key: str) -> Path:
        # Prevent path traversal outside the storage root.
        candidate = (self.root / key).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise ValueError("invalid storage key")
        return candidate

    async def put(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.is_file():
            return None
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    async def exists(self, key: str) -> bool:
        return self._path(key).is_file()
