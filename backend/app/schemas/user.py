import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator

from app.core.permissions import Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Role = Role.LECTURE

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    # Coordonnées du compte (agence/gestionnaire). Le RIB du bailleur est sur la fiche.
    phone: Optional[str] = None
    address: Optional[str] = None  # rue (n° + voie)
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    # Nom et prénom du propriétaire (bailleur) — pour bail / attestation / tiers payant.
    owner_full_name: Optional[str] = None
    owner_company: Optional[str] = None
    owner_national_id: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Mise à jour de son propre profil (utilisateur connecté).
    full_name = nom de la résidence ; owner_full_name = nom et prénom du propriétaire."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None  # rue (n° + voie)
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    # Identité bailleur : nom/prénom (GP) + société/SCI + SIREN/SIRET (mandataire ET GP).
    owner_full_name: Optional[str] = None
    owner_company: Optional[str] = None
    owner_national_id: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: Role


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v


class AdminPasswordReset(BaseModel):
    """Réinitialisation du mot de passe d'un utilisateur par un gestionnaire/admin
    (sans connaître l'ancien mot de passe)."""
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    phone: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    owner_full_name: Optional[str] = None
    owner_company: Optional[str] = None
    owner_national_id: Optional[str] = None
    logo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserMeResponse(UserResponse):
    """Réponse pour /auth/me — peut être étendue avec des données supplémentaires."""
    pass
