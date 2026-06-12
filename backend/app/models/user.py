import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

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
    # Adresse postale structurée (même format que les biens) : rue / CP / ville / pays.
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)  # rue (n° + voie)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    # Type d'identité du bailleur : 'personne' (Prénom/Nom) ou 'societe' (Société/SCI).
    # Détermine le nom affiché sur les documents (bail, attestations).
    owner_kind: Mapped[str] = mapped_column(String(10), nullable=False, default="personne", server_default="personne")
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
    # « Ma papeterie » : variables épinglées par l'utilisateur, par type de document.
    # Forme : { "<template_type>": ["{{var}}", …], … }. Null/absent = aucune épingle.
    template_pinned_vars: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

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

    # ── Visibilité de l'espace propriétaire (lecture seule) ───────────────────
    # Liste de clés de rubriques (cf. core.proprio_sections). Null = non défini.
    # Sur un compte PROPRIÉTAIRE : surcharge individuelle (prioritaire).
    proprio_visibility: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Sur le compte GESTIONNAIRE (racine d'agence) : défaut appliqué à tous ses
    # propriétaires qui n'ont pas de surcharge.
    proprio_visibility_default: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    @property
    def full_address(self) -> Optional[str]:
        """Adresse postale recomposée sur une ligne : « rue, CP Ville [, Pays] ».
        Consommée par la génération de documents (en-tête émetteur). None si vide."""
        loc = " ".join(p for p in [(self.zip_code or "").strip(), (self.city or "").strip()] if p)
        country = (self.country or "").strip()
        parts = [
            (self.address or "").strip(),
            loc,
            country if country and country.lower() != "france" else "",
        ]
        joined = ", ".join(p for p in parts if p)
        return joined or None

    @property
    def bailleur_name(self) -> Optional[str]:
        """Nom du bailleur pour les documents (bail, attestations), selon le type :
        société → dénomination (owner_company) ; personne → owner_full_name.
        Repli sur l'autre champ si le champ attendu est vide."""
        company = (self.owner_company or "").strip()
        person = (self.owner_full_name or "").strip()
        if (self.owner_kind or "personne") == "societe":
            return company or person or None
        return person or company or None

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
