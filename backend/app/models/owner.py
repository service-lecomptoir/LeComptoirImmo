import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin
from app.models.tenant import Civility  # même énumération de civilité que les locataires

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.document import Document


class Owner(Base, TimestampMixin):
    """Fiche propriétaire (bailleur). Sert aux contrats et à l'affichage côté
    locataire (coordonnées de règlement). Le compte de connexion est OPTIONNEL :
    `user_id` lie la fiche à un compte utilisateur (rôle proprietaire) mais une
    fiche peut exister sans aucun compte en ligne."""
    __tablename__ = "owners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Identifiant lisible unique de la fiche propriétaire (ex. « PR-00001 »).
    ref_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Identité ──────────────────────────────────────────────────────────────
    civility: Mapped[Optional[str]] = mapped_column(
        SAEnum(Civility, name="civility_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]), nullable=True
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    # Personne morale (SCI, société…) — prioritaire sur prénom/nom à l'affichage
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # SIRET / n° pièce

    # ── Contact ───────────────────────────────────────────────────────────────
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # Adresse postale structurée (même format que les biens) : rue / CP / ville / pays.
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)  # rue (n° + voie)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # ── Coordonnées bancaires (RIB) — communiquées au locataire pour le règlement ─
    iban: Mapped[Optional[str]] = mapped_column(String(34), nullable=True)
    bic: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_holder: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # ── Compte propriétaire (connexion en ligne, optionnel) ─────────────────────
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    properties: Mapped[list["Property"]] = relationship(
        "Property", back_populates="owner", lazy="select",
        foreign_keys="Property.owner_id",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        primaryjoin="and_(Document.entity_type=='owner', "
                    "foreign(Document.entity_id)==Owner.id)",
        viewonly=True,
        lazy="select",
    )

    @property
    def full_name(self) -> str:
        if self.company_name:
            return self.company_name
        # « Prénom Nom » sans la civilité (séparée du nom, cf. documents/listes).
        parts = [self.first_name or "", self.last_name]
        return " ".join(p for p in parts if p).strip()

    @property
    def full_address(self) -> Optional[str]:
        """Adresse postale recomposée sur une ligne : « rue, CP Ville [, Pays] ».
        Format consommé par la génération de documents (lettres, quittances) qui
        re-découpe ensuite en lignes. None si aucune composante."""
        loc = " ".join(p for p in [(self.zip_code or "").strip(), (self.city or "").strip()] if p)
        country = (self.country or "").strip()
        # Le pays n'est ajouté que s'il diffère de « France » (implicite par défaut).
        parts = [
            (self.address or "").strip(),
            loc,
            country if country and country.lower() != "france" else "",
        ]
        joined = ", ".join(p for p in parts if p)
        return joined or None

    def __repr__(self) -> str:
        return f"<Owner {self.full_name}>"
