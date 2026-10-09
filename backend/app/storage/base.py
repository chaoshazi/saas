"""Storage backend abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """Store bytes and return a retrievable location/key."""

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Return stored bytes or None when missing."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove a stored object."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return whether an object exists."""
