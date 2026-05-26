import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.ticket import TicketStatus, TicketPriority, TicketCategory


class TicketMessageBase(BaseModel):
    content: str
    is_internal: bool = False


class TicketMessageCreate(TicketMessageBase):
    pass


class TicketMessageResponse(TicketMessageBase):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketCreate(BaseModel):
    title: str
    description: str
    category: TicketCategory = TicketCategory.AUTRE
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    assigned_to_id: Optional[uuid.UUID] = None


class TicketResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: str
    status: str
    priority: str
    tenant_id: uuid.UUID
    tenant_name: Optional[str] = None
    lease_id: Optional[uuid.UUID] = None
    assigned_to_id: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    closed_at: Optional[datetime] = None
    messages: list[TicketMessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketListItem(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    status: str
    priority: str
    tenant_id: uuid.UUID
    tenant_name: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
