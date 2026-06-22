import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.core.permissions import Role


class UserCreate(BaseModel):
    email: EmailStr
    # Le mot de passe est facultatif : s'il est vide, il est auto-généré côté
    # serveur et envoyé par e-mail à l'utilisateur (transparent pour le gestionnaire).
    password: str | None = None
    full_name: str
    role: Role = Role.LECTURE
    # Téléphone (repris de la fiche locataire à la création du compte).
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    # Coordonnées du compte (agence/gestionnaire). Le RIB du bailleur est sur la fiche.
    phone: str | None = None
    address: str | None = None  # rue (n° + voie)
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    # Identité bailleur : type (personne/societe) + nom/prénom OU société + SIREN/SIRET.
    owner_kind: str | None = None
    owner_full_name: str | None = None
    owner_company: str | None = None
    owner_national_id: str | None = None
    # « Atelier de documents » : variables épinglées par type de document.
    template_pinned_vars: dict | None = None
    # Thème d'apparence des e-mails ('marine_center'|'marine_band'|'epure').
    email_theme: str | None = None
    # Signature numérique (data-URL PNG) apposée sur les documents générés.
    signature: str | None = None
    # Source de la signature (pour réédition) : mode 'type'|'draw', texte, police.
    signature_mode: str | None = None
    signature_text: str | None = None
    signature_font: str | None = None
    # Tampon / cachet professionnel (data-URL PNG).
    tampon: str | None = None
    # Honoraires de gestion (mandataire) : taux par défaut + TVA applicable.
    mgmt_fee_rate: float | None = None
    mgmt_fee_vat_rate: float | None = None


class ProfileUpdate(BaseModel):
    """Mise à jour de son propre profil (utilisateur connecté).
    full_name = nom de la résidence ; owner_full_name = nom et prénom du propriétaire."""

    full_name: str | None = None
    phone: str | None = None
    address: str | None = None  # rue (n° + voie)
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    # Identité bailleur : type + nom/prénom (personne) OU société/SCI + SIREN/SIRET.
    owner_kind: str | None = None
    owner_full_name: str | None = None
    owner_company: str | None = None
    owner_national_id: str | None = None
    # « Atelier de documents » : variables épinglées par type de document.
    template_pinned_vars: dict | None = None


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
    ref_code: str | None = None
    email: str
    full_name: str
    role: Role
    is_active: bool
    must_change_password: bool = False
    phone: str | None = None
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    owner_kind: str | None = None
    owner_full_name: str | None = None
    owner_company: str | None = None
    owner_national_id: str | None = None
    template_pinned_vars: dict | None = None
    logo_url: str | None = None
    email_theme: str | None = None
    signature: str | None = None
    signature_mode: str | None = None
    signature_text: str | None = None
    signature_font: str | None = None
    tampon: str | None = None
    mgmt_fee_rate: float | None = None
    mgmt_fee_vat_rate: float | None = None
    last_login_at: datetime | None = None
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
    proprio_visibility: list | None = None
    proprio_visibility_default: list | None = None
    # Rubriques effectivement visibles par CE propriétaire (calculé ∩ plan).
    proprio_sections: list | None = None
