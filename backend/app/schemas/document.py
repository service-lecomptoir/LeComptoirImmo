import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentType, EntityType


class DocumentResponse(BaseModel):
    id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID
    document_type: DocumentType
    file_name: str
    mime_type: str
    file_size: int | None
    label: str | None
    notes: str | None
    uploaded_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    document_type: DocumentType | None = None
    label: str | None = None
    notes: str | None = None
