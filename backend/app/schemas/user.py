import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator

from app.core.permissions import Role


class UserCreate(BaseModel):
    email: EmailStr
    # Le mot de passe est facultatif : s'il est vide, il est auto-généré côté
    # serveur et envoyé par e-mail à l'utilisateur (transparent pour le gestionnaire).
    password: Optional[str] = None
    full_name: str
    role: Role = Role.LECTURE
    # Téléphone (repris de la fiche locataire à la création du compte).
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
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
    # Identité bailleur : type (personne/societe) + nom/prénom OU société + SIREN/SIRET.
    owner_kind: Optional[str] = None
    owner_full_name: Optional[str] = None
    owner_company: Optional[str] = None
    owner_national_id: Optional[str] = None
    # « Atelier de documents » : variables épinglées par type de document.
    template_pinned_vars: Optional[dict] = None
    # Signature numérique (data-URL PNG) apposée sur les documents générés.
    signature: Optional[str] = None
    # Source de la signature (pour réédition) : mode 'type'|'draw', texte, police.
    signature_mode: Optional[str] = None
    signature_text: Optional[str] = None
    signature_font: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Mise à jour de son propre profil (utilisateur connecté).
    full_name = nom de la résidence ; owner_full_name = nom et prénom du propriétaire."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None  # rue (n° + voie)
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    # Identité bailleur : type + nom/prénom (personne) OU société/SCI + SIREN/SIRET.
    owner_kind: Optional[str] = None
    owner_full_name: Optional[str] = None
    owner_company: Optional[str] = None
    owner_national_id: Optional[str] = None
    # « Atelier de documents » : variables épinglées par type de document.
    template_pinned_vars: Optional[dict] = None


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
    ref_code: Optional[str] = None
    email: str
    full_name: str
    role: Role
    is_active: bool
    must_change_password: bool = False
    phone: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    owner_kind: Optional[str] = None
    owner_full_name: Optional[str] = None
    owner_company: Optional[str] = None
    owner_national_id: Optional[str] = None
    template_pinned_vars: Optional[dict] = None
    logo_url: Optional[str] = None
    signature: Optional[str] = None
    signature_mode: Optional[str] = None
    signature_text: Optional[str] = None
    signature_font: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCreateResponse(UserResponse):
    """Réponse de création de compte : indique si le mot de passe auto-généré
    a bien été envoyé par e-mail à l'utilisateur."""
    credentials_email_sent: bool = False


class UserMeResponse(UserResponse):
    """Réponse pour /auth/me — peut être étendue avec des données supplémentaires."""
    # Visibilité espace propriétaire : réglages bruts (pour les écrans gestionnaire)
    proprio_visibility: Optional[list] = None
    proprio_visibility_default: Optional[list] = None
    # Rubriques effectivement visibles par CE propriétaire (calculé ∩ plan).
    proprio_sections: Optional[list] = None
