import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Numeric, Enum as SAEnum, ForeignKey
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
    phone2: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

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
        # « Nom Prénom » sans la civilité (séparée du nom, cf. documents/listes).
        parts = [self.last_name, self.first_name or ""]
        return " ".join(p for p in parts if p).strip()

    def __repr__(self) -> str:
        return f"<Owner {self.full_name}>"
