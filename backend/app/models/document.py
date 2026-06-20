import uuid
from enum import Enum

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class EntityType(str, Enum):
    TENANT = "tenant"
    OWNER = "owner"
    LEASE = "lease"
    UNIT = "unit"
    PROPERTY = "property"
    INSPECTION = "inspection"


class DocumentType(str, Enum):
    # Documents locataire
    CNI = "cni"
    PASSEPORT = "passeport"
    JUSTIFICATIF_DOMICILE = "justificatif_domicile"
    JUSTIFICATIF_REVENUS = "justificatif_revenus"
    AVIS_IMPOSITION = "avis_imposition"
    # Documents contrat
    CONTRAT_BAIL = "contrat_bail"
    AVENANT = "avenant"
    # Documents financiers
    QUITTANCE = "quittance"
    ATTESTATION_CAF = "attestation_caf"
    ATTESTATION_TIERS = "attestation_tiers"
    # Autres
    ETAT_DES_LIEUX = "etat_des_lieux"
    PHOTO = "photo"
    AUTRE = "autre"
    # Documents locataire (uploadables par le locataire)
    ASSURANCE = "assurance"
    REGULARISATION_CHARGES = "regularisation_charges"
    REVISION_LOYER = "revision_loyer"
    TAXE_ORDURES = "taxe_ordures"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Relation polymorphique ─────────────────────────────────────────────────
    entity_type: Mapped[str] = mapped_column(
        SAEnum(
            EntityType,
            name="entity_type_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # ── Type de document ──────────────────────────────────────────────────────
    document_type: Mapped[str] = mapped_column(
        SAEnum(
            DocumentType,
            name="document_type_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=DocumentType.AUTRE,
    )

    # ── Fichier ───────────────────────────────────────────────────────────────
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # ── Métadonnées ───────────────────────────────────────────────────────────
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Document {self.document_type} : {self.file_name}>"
