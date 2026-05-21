import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.notification import NotificationType, NotificationPriority


class NotificationCreate(BaseModel):
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None  # None = broadcast


class NotificationResponse(BaseModel):
    id: uuid.UUID
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    is_read: bool
    read_at: Optional[datetime] = None
    user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int
