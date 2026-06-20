import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class CafTemplate(Base, TimestampMixin):
    """Modèle PDF officiel CAF uploadé par le gestionnaire (CERFA fillable).

    Le gestionnaire téléverse le formulaire officiel (attestation de loyer ou
    formulaire de tiers payant) ; on en extrait les champs AcroForm puis on les
    associe aux données de l'application (`field_map` : champ PDF → clé de donnée).
    La génération remplit ce PDF et y appose la signature. Un modèle par
    (gestionnaire, type de document)."""

    __tablename__ = "caf_templates"
    __table_args__ = (UniqueConstraint("gestionnaire_id", "doc_type", name="uq_caf_tpl_gest_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gestionnaire_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 'attestation' | 'tiers_payant'
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Mapping {nom_du_champ_pdf: clé_de_donnée} (clés : voir caf_data.DATA_KEYS).
    field_map: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Signature : page (1-based) + position/échelle (mm) pour l'apposition.
    sign_page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sign_x_mm: Mapped[int] = mapped_column(Integer, nullable=False, default=130)
    sign_y_mm: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    sign_w_mm: Mapped[int] = mapped_column(Integer, nullable=False, default=45)

    def __repr__(self) -> str:
        return f"<CafTemplate {self.doc_type} gest={self.gestionnaire_id}>"
