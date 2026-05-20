import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.document import EntityType, DocumentType


class DocumentResponse(BaseModel):
    id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID
    document_type: DocumentType
    file_name: str
    mime_type: str
    file_size: Optional[int]
    label: Optional[str]
    notes: Optional[str]
    uploaded_by: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    document_type: Optional[DocumentType] = None
    label: Optional[str] = None
    notes: Optional[str] = None
