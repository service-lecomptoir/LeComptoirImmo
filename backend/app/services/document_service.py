import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile

from app.models.document import Document, EntityType, DocumentType
from app.schemas.document import DocumentUpdate
from app.utils.file_handler import save_file, delete_file
from app.core.exceptions import NotFoundException


class DocumentService:

    @staticmethod
    async def upload(
        db: AsyncSession,
        file: UploadFile,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        document_type: DocumentType,
        label: str | None,
        notes: str | None,
        uploaded_by: uuid.UUID,
    ) -> Document:
        file_path, file_size = await save_file(file, entity_type.value, str(entity_id))

        doc = Document(
            entity_type=entity_type,
            entity_id=entity_id,
            document_type=document_type,
            file_name=file.filename or "document",
            file_path=file_path,
            mime_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            label=label,
            notes=notes,
            uploaded_by=uploaded_by,
        )
        db.add(doc)
        await db.flush()
        return doc

    @staticmethod
    async def list_for_entities(
        db: AsyncSession,
        entity_ids: List[uuid.UUID],
        entity_type: Optional[EntityType] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Document]:
        """Retourne les documents liés à une liste d'entités (tenant, lease, etc.)."""
        q = select(Document).where(Document.entity_id.in_(entity_ids))
        if entity_type:
            q = q.where(Document.entity_type == entity_type)
        q = q.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def list_all(
        db: AsyncSession,
        entity_type: Optional[EntityType] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Document]:
        """Retourne tous les documents (gestionnaire/admin)."""
        q = select(Document)
        if entity_type:
            q = q.where(Document.entity_type == entity_type)
        q = q.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def list_by_entity(
        db: AsyncSession,
        entity_type: EntityType,
        entity_id: uuid.UUID,
    ) -> List[Document]:
        result = await db.execute(
            select(Document)
            .where(
                Document.entity_type == entity_type,
                Document.entity_id == entity_id,
            )
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, doc_id: uuid.UUID) -> Document:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundException("Document", str(doc_id))
        return doc

    @staticmethod
    async def update(
        db: AsyncSession, doc_id: uuid.UUID, data: DocumentUpdate
    ) -> Document:
        doc = await DocumentService.get_by_id(db, doc_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)
        await db.flush()
        return doc

    @staticmethod
    async def delete(db: AsyncSession, doc_id: uuid.UUID) -> None:
        doc = await DocumentService.get_by_id(db, doc_id)
        delete_file(doc.file_path)
        await db.delete(doc)
        await db.flush()
