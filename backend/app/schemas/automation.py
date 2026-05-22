import uuid
from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel
from app.models.automation import RuleType, Channel


class AutomationRuleCreate(BaseModel):
    name: str
    rule_type: RuleType
    trigger_days: int = 5
    channel: Channel = Channel.EMAIL
    subject: Optional[str] = None
    body_template: Optional[str] = None
    is_active: bool = True
    filter_config: Optional[Dict[str, Any]] = None


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_days: Optional[int] = None
    channel: Optional[Channel] = None
    subject: Optional[str] = None
    body_template: Optional[str] = None
    is_active: Optional[bool] = None
    filter_config: Optional[Dict[str, Any]] = None


class AutomationRuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    rule_type: RuleType
    trigger_days: int
    channel: Channel
    subject: Optional[str] = None
    body_template: Optional[str] = None
    is_active: bool
    filter_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommunicationLogResponse(BaseModel):
    id: uuid.UUID
    rule_id: Optional[uuid.UUID] = None
    tenant_id: Optional[uuid.UUID] = None
    lease_id: Optional[uuid.UUID] = None
    channel: str
    recipient: Optional[str] = None
    subject: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    sent_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class GroupCommunicationRequest(BaseModel):
    subject: str
    body: str
    channel: Channel = Channel.EMAIL
    # Filtres optionnels
    property_ids: Optional[list[uuid.UUID]] = None
    all_tenants: bool = True
    tenant_ids: Optional[list[uuid.UUID]] = None
