import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator

MAJORITIES = ("art24", "art25", "art26", "unanimite")
CHOICES = ("pour", "contre", "abstention")


# ── Assemblée ────────────────────────────────────────────────────────────────
class AssemblyCreate(BaseModel):
    title: str
    kind: str = "ordinaire"
    meeting_date: date | None = None
    location: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Le titre de l'assemblée est requis.")
        return v


class AssemblyUpdate(BaseModel):
    title: str | None = None
    kind: str | None = None
    meeting_date: date | None = None
    location: str | None = None
    status: str | None = None
    notes: str | None = None


class AssemblyListItem(BaseModel):
    id: uuid.UUID
    title: str
    kind: str
    meeting_date: date | None = None
    status: str
    resolution_count: int = 0
    created_at: datetime


# ── Résolutions + votes ──────────────────────────────────────────────────────
class ResolutionCreate(BaseModel):
    title: str
    description: str | None = None
    majority: str = "art24"
    position: int = 0

    @field_validator("majority")
    @classmethod
    def valid_majority(cls, v: str) -> str:
        if v not in MAJORITIES:
            raise ValueError("Règle de majorité invalide.")
        return v


class ResolutionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    majority: str | None = None
    position: int | None = None


class VoteIn(BaseModel):
    owner_id: uuid.UUID
    choice: str

    @field_validator("choice")
    @classmethod
    def valid_choice(cls, v: str) -> str:
        if v not in CHOICES:
            raise ValueError("Vote invalide (pour / contre / abstention).")
        return v


class VoteRow(BaseModel):
    owner_id: uuid.UUID
    owner_name: str | None = None
    choice: str
    tantiemes: float = 0


class ResolutionResult(BaseModel):
    id: uuid.UUID
    position: int
    title: str
    description: str | None = None
    majority: str
    outcome: str
    outcome_note: str | None = None
    base_tantiemes: int = 0
    pour: float = 0
    contre: float = 0
    abstention: float = 0
    votes: list[VoteRow] = []


class AssemblyDetail(BaseModel):
    id: uuid.UUID
    copropriete_id: uuid.UUID
    title: str
    kind: str
    meeting_date: date | None = None
    location: str | None = None
    status: str
    notes: str | None = None
    resolutions: list[ResolutionResult] = []
    created_at: datetime
    updated_at: datetime


class VoterRow(BaseModel):
    """Copropriétaire votant : poids = somme de ses tantièmes sur la clé générale."""

    owner_id: uuid.UUID
    owner_name: str | None = None
    tantiemes: float = 0
