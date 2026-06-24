import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class ResidenceBoutiqueLink(Base, TimestampMixin):
    """Lien entre une résidence Immo (un bien « property » ou une copropriété
    « copropriete ») et une boutique Le Comptoir Market.

    Pont inter-produits : le provisionnement est orchestré par Alice (qui rapproche
    le gestionnaire de son gérant Market par e-mail). Ce lien mémorise, côté Immo,
    la boutique rattachée pour l'afficher au gestionnaire et plus tard au locataire.
    """

    __tablename__ = "residence_boutique_links"
    __table_args__ = (
        UniqueConstraint("residence_kind", "residence_id", name="uq_residence_boutique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 'property' (bien) ou 'copropriete' (immeuble en copropriété).
    residence_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    residence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # Gestionnaire (created_by de la résidence) à l'origine du lien.
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    boutique_id: Mapped[str] = mapped_column(String(64), nullable=False)
    boutique_slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    boutique_url: Mapped[str | None] = mapped_column(String(400), nullable=True)

    def __repr__(self) -> str:
        return f"<ResidenceBoutiqueLink {self.residence_kind}:{self.residence_id}>"
