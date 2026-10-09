"""Document and version endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.document import Document, DocumentVersion
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate, DocumentVersionRead

router = APIRouter(tags=["documents"])


async def _get_document(db: AsyncSession, document_id: int) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id).options(selectinload(Document.creator))
    )
    if document is None:
        raise NotFoundError("Document not found")
    return document


@router.get("/documents", response_model=list[DocumentRead])
async def list_documents(
    project_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentRead]:
    query = select(Document).options(selectinload(Document.creator)).order_by(Document.updated_at.desc())
    if project_id is not None:
        query = query.where(Document.project_id == project_id)
    documents = (await db.scalars(query)).all()
    return [DocumentRead.model_validate(document) for document in documents]


@router.post("/documents", response_model=DocumentRead, status_code=201)
async def create_document(
    payload: DocumentCreate,
    user: User = Depends(require_permission("document.manage")),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    document = Document(
        project_id=payload.project_id,
        creator_id=user.id,
        title=payload.title,
        content=payload.content,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    document = await _get_document(db, document.id)
    return DocumentRead.model_validate(document)


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    return DocumentRead.model_validate(await _get_document(db, document_id))


@router.patch("/documents/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    payload: DocumentUpdate,
    user: User = Depends(require_permission("document.manage")),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    document = await _get_document(db, document_id)
    data = payload.model_dump(exclude_unset=True)
    change_note = data.pop("change_note", None)
    if "content" in data and data["content"] != document.content:
        db.add(DocumentVersion(
            document_id=document.id,
            author_id=user.id,
            version=document.version,
            content=document.content,
            change_note=change_note,
        ))
        document.version += 1
    for field, value in data.items():
        setattr(document, field, value)
    await db.commit()
    document = await _get_document(db, document.id)
    return DocumentRead.model_validate(document)


@router.get("/documents/{document_id}/versions", response_model=list[DocumentVersionRead])
async def list_versions(
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentVersionRead]:
    await _get_document(db, document_id)
    versions = (await db.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version.desc())
    )).all()
    return [DocumentVersionRead.model_validate(version) for version in versions]
