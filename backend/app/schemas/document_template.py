import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.document_template import TemplateType


class DocumentTemplateCreate(BaseModel):
    name: str
    template_type: TemplateType
    header_color: Optional[str] = "#1E3A5F"
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_siret: Optional[str] = None
    content_html: Optional[str] = None
    footer_text: Optional[str] = None
    is_default: bool = False
    is_active: bool = True


class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    header_color: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_siret: Optional[str] = None
    content_html: Optional[str] = None
    footer_text: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class DocumentTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    template_type: TemplateType
    logo_url: Optional[str] = None
    header_color: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_siret: Optional[str] = None
    content_html: Optional[str] = None
    footer_text: Optional[str] = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
