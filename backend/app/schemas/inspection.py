import uuid
from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel

from app.models.inspection import InspectionType, OverallCondition


class InspectionCreate(BaseModel):
    lease_id: Optional[uuid.UUID] = None
    unit_id: uuid.UUID
    inspection_type: InspectionType
    inspection_date: date
    inspector_name: Optional[str] = None
    tenant_present: bool = True
    overall_condition: Optional[OverallCondition] = None
    notes: Optional[str] = None
    rooms_data: Optional[dict[str, Any]] = None


class InspectionUpdate(BaseModel):
    inspection_date: Optional[date] = None
    inspector_name: Optional[str] = None
    tenant_present: Optional[bool] = None
    overall_condition: Optional[OverallCondition] = None
    notes: Optional[str] = None
    rooms_data: Optional[dict[str, Any]] = None


class InspectionResponse(BaseModel):
    id: uuid.UUID
    lease_id: Optional[uuid.UUID] = None
    unit_id: uuid.UUID
    inspection_type: InspectionType
    inspection_date: date
    inspector_name: Optional[str] = None
    tenant_present: bool
    overall_condition: Optional[OverallCondition] = None
    notes: Optional[str] = None
    rooms_data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InspectionListResponse(BaseModel):
    items: list[InspectionResponse]
    total: int
    skip: int
    limit: int
