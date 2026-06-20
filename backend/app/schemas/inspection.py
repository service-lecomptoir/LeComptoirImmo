import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.models.inspection import InspectionType, OverallCondition


class InspectionCreate(BaseModel):
    lease_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    inspection_type: InspectionType
    inspection_date: date
    inspector_name: str | None = None
    tenant_present: bool = True
    overall_condition: OverallCondition | None = None
    notes: str | None = None
    rooms_data: dict[str, Any] | None = None


class InspectionUpdate(BaseModel):
    inspection_date: date | None = None
    inspector_name: str | None = None
    tenant_present: bool | None = None
    overall_condition: OverallCondition | None = None
    notes: str | None = None
    rooms_data: dict[str, Any] | None = None


class InspectionResponse(BaseModel):
    id: uuid.UUID
    lease_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    inspection_type: InspectionType
    inspection_date: date
    inspector_name: str | None = None
    tenant_present: bool
    overall_condition: OverallCondition | None = None
    notes: str | None = None
    rooms_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InspectionListResponse(BaseModel):
    items: list[InspectionResponse]
    total: int
    skip: int
    limit: int
