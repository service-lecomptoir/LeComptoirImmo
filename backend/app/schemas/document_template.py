import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.document_template import TemplateType


class DocumentTemplateCreate(BaseModel):
    name: str
    template_type: TemplateType
    header_color: str | None = "#1E3A5F"
    company_name: str | None = None
    company_address: str | None = None
    company_phone: str | None = None
    company_email: str | None = None
    company_siret: str | None = None
    content_html: str | None = None
    footer_text: str | None = None
    blocks: list[Any] | None = None
    theme: dict[str, Any] | None = None
    is_default: bool = False
    is_active: bool = True


class DocumentTemplateUpdate(BaseModel):
    name: str | None = None
    header_color: str | None = None
    company_name: str | None = None
    company_address: str | None = None
    company_phone: str | None = None
    company_email: str | None = None
    company_siret: str | None = None
    content_html: str | None = None
    footer_text: str | None = None
    blocks: list[Any] | None = None
    theme: dict[str, Any] | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class DocumentTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    template_type: TemplateType
    logo_url: str | None = None
    header_color: str | None = None
    company_name: str | None = None
    company_address: str | None = None
    company_phone: str | None = None
    company_email: str | None = None
    company_siret: str | None = None
    content_html: str | None = None
    footer_text: str | None = None
    blocks: list[Any] | None = None
    theme: dict[str, Any] | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
