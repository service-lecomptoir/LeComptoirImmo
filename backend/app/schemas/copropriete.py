import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


# ── Copropriété ──────────────────────────────────────────────────────────────
class CoproprieteCreate(BaseModel):
    name: str
    immatriculation: str | None = None
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    construction_year: int | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def name_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Le nom de la copropriété est requis.")
        return v


class CoproprieteUpdate(BaseModel):
    name: str | None = None
    immatriculation: str | None = None
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    construction_year: int | None = None
    notes: str | None = None


class CoproprieteListItem(BaseModel):
    id: uuid.UUID
    ref_code: str | None = None
    name: str
    city: str | None = None
    immatriculation: str | None = None
    lot_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Clés de répartition ──────────────────────────────────────────────────────
class RepartitionKeyCreate(BaseModel):
    name: str
    total_tantiemes: int = 10000
    is_general: bool = False
    position: int = 0

    @field_validator("total_tantiemes")
    @classmethod
    def total_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("La base de tantièmes doit être supérieure à 0.")
        return v


class RepartitionKeyUpdate(BaseModel):
    name: str | None = None
    total_tantiemes: int | None = None
    is_general: bool | None = None
    position: int | None = None


class RepartitionKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    total_tantiemes: int
    is_general: bool
    position: int
    # Somme des tantièmes affectés aux lots pour cette clé + cohérence avec la base.
    assigned_tantiemes: float = 0
    balanced: bool = True


# ── Lots ─────────────────────────────────────────────────────────────────────
class LotTantiemeIn(BaseModel):
    key_id: uuid.UUID
    tantiemes: float = 0


class LotCreate(BaseModel):
    numero: str
    lot_type: str | None = None
    floor: str | None = None
    description: str | None = None
    owner_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    tantiemes: list[LotTantiemeIn] = []

    @field_validator("numero")
    @classmethod
    def numero_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Le numéro de lot est requis.")
        return v


class LotUpdate(BaseModel):
    numero: str | None = None
    lot_type: str | None = None
    floor: str | None = None
    description: str | None = None
    owner_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    tantiemes: list[LotTantiemeIn] | None = None


class LotResponse(BaseModel):
    id: uuid.UUID
    numero: str
    lot_type: str | None = None
    floor: str | None = None
    description: str | None = None
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    property_id: uuid.UUID | None = None
    # Tantièmes par clé : { key_id (str) : valeur }.
    tantiemes: dict[str, float] = {}


class CoproprieteDetail(BaseModel):
    id: uuid.UUID
    ref_code: str | None = None
    name: str
    immatriculation: str | None = None
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    construction_year: int | None = None
    notes: str | None = None
    keys: list[RepartitionKeyResponse] = []
    lots: list[LotResponse] = []
    created_at: datetime
    updated_at: datetime
