import uuid
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel


class SubscriptionRequestOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None
    source: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SubscriptionRequestUpdate(BaseModel):
    status: Optional[Literal["nouveau", "en_cours", "traite", "rejete"]] = None
    notes: Optional[str] = None
