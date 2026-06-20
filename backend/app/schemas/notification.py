import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationPriority, NotificationType


class NotificationCreate(BaseModel):
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    message: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None  # None = broadcast


class NotificationResponse(BaseModel):
    id: uuid.UUID
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    is_read: bool
    read_at: datetime | None = None
    user_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int
