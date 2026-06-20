import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.automation import Channel, RuleType


class AutomationRuleCreate(BaseModel):
    name: str
    rule_type: RuleType
    trigger_days: int = 5
    run_hour: int = 8
    run_minute: int = 0
    channel: Channel = Channel.EMAIL
    auto_generate: bool = True
    auto_deposit: bool = True
    send_email: bool = True
    send_sms: bool = False
    subject: str | None = None
    body_template: str | None = None
    is_active: bool = True
    filter_config: dict[str, Any] | None = None
    # Adresse(s) en copie (CC) des e-mails de cette règle, séparées par des virgules
    # (ex. l'e-mail du gestionnaire). Vide = aucune copie.
    cc_emails: str | None = None
    # Signature (nom du service) affichée en bas des e-mails.
    signature: str | None = None


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    trigger_days: int | None = None
    run_hour: int | None = None
    run_minute: int | None = None
    channel: Channel | None = None
    auto_generate: bool | None = None
    auto_deposit: bool | None = None
    send_email: bool | None = None
    send_sms: bool | None = None
    subject: str | None = None
    body_template: str | None = None
    is_active: bool | None = None
    filter_config: dict[str, Any] | None = None
    cc_emails: str | None = None
    signature: str | None = None


class AutomationRuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    rule_type: RuleType
    trigger_days: int
    run_hour: int = 8
    run_minute: int = 0
    last_run_at: datetime | None = None
    channel: Channel
    auto_generate: bool = True
    auto_deposit: bool = True
    send_email: bool = True
    send_sms: bool = False
    subject: str | None = None
    body_template: str | None = None
    is_active: bool
    filter_config: dict[str, Any] | None = None
    cc_emails: str | None = None
    signature: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommunicationLogResponse(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    lease_id: uuid.UUID | None = None
    channel: str
    recipient: str | None = None
    subject: str | None = None
    status: str
    error_message: str | None = None
    sent_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class GroupCommunicationRequest(BaseModel):
    subject: str
    body: str
    channel: Channel = Channel.EMAIL
    # Adresse(s) en copie (CC), séparées par des virgules (ex. le gestionnaire).
    cc_emails: str | None = None
    # Filtres optionnels
    property_ids: list[uuid.UUID] | None = None
    all_tenants: bool = True
    tenant_ids: list[uuid.UUID] | None = None
