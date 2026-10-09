"""Task attachment schema."""
from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMModel


class TaskAttachmentRead(ORMModel):
    id: int
    task_id: int
    uploader_id: int
    filename: str
    content_type: str | None
    size: int
    storage_key: str
    created_at: datetime
