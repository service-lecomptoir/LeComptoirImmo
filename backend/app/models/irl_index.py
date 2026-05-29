import uuid
from sqlalchemy import Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin


class IrlIndex(Base, TimestampMixin):
    """Indice de Référence des Loyers (IRL) publié par l'INSEE, par trimestre.

    Sert au calcul de la révision annuelle du loyer :
        nouveau_loyer = loyer_actuel × (IRL_récent / IRL_de_référence)
    Renseigné manuellement et/ou via récupération INSEE (best-effort)."""
    __tablename__ = "irl_indices"
    __table_args__ = (
        UniqueConstraint("year", "quarter", name="uq_irl_year_quarter"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..4
    value: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manuel")  # manuel | insee

    def __repr__(self) -> str:
        return f"<IrlIndex {self.year}-T{self.quarter} = {self.value}>"
