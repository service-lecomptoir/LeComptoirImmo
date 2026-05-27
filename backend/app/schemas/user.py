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
    # RIB — un gestionnaire peut renseigner le RIB d'un propriétaire à sa place
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_holder: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Mise à jour de son propre profil (utilisateur connecté)."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    # Coordonnées bancaires (propriétaire/GP) — servent au virement du locataire
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_holder: Optional[str] = None


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


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    phone: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_holder: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserMeResponse(UserResponse):
    """Réponse pour /auth/me — peut être étendue avec des données supplémentaires."""
    pass
