import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin
from app.core.permissions import Role


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum(Role, name="user_role", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        # Valeurs actives : admin, gestionnaire, proprietaire, locataire
        nullable=False,
        default=Role.LECTURE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Coordonnées (profil — agence/gestionnaire) ────────────────────────────
    # full_name = NOM DE LA RÉSIDENCE (marque/affichage partout).
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # Nom et prénom du propriétaire (bailleur) — utilisé pour le bail, l'attestation
    # de loyer et le formulaire tiers payant. Distinct du nom de la résidence.
    owner_full_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    # Société / SCI du bailleur (mandataire = société ; GP = SCI le cas échéant)
    owner_company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # SIRET / N° de pièce d'identité du bailleur
    owner_national_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Logo du gestionnaire (« Mes informations ») — affiché en en-tête des documents
    # (avis d'échéance, mise en page moderne, à la place du logo).
    logo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # NB : le RIB du bailleur vit désormais sur la fiche propriétaire (table owners),
    # plus sur le compte utilisateur (colonnes iban/bic/bank_holder supprimées).

    # Audit : qui a créé cet utilisateur (utile pour l'isolation GP)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Isolation multi-agences : racine de la chaîne created_by (= compte principal).
    # NULL pour un compte principal (alors COALESCE(agency_id, id) = id le désigne lui-même) ;
    # = l'id du principal pour un sous-compte. Détermine le périmètre « agence ».
    agency_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
