import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Enum as SAEnum, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base, TimestampMixin
from app.core.permissions import Role


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Identifiant lisible unique attribué à la création (ex. « GM-00001 »). Le
    # préfixe dépend du rôle (GM/GP/UP/UL/AD/CB/LE). Sert de « numéro associé »
    # affiché dans l'app (avatar) et les documents.
    ref_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
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
    # Mot de passe temporaire (compte gestionnaire provisionné par Alice ou
    # réinitialisé par un admin) : tant que True, l'utilisateur est forcé de
    # définir un nouveau mot de passe à sa prochaine connexion.
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )

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
    # Signature numérique (data-URL PNG, fond blanc) apposée en bas des courriers
    # générés (lettre de relance, plan d'apurement…). Réglée dans « Mes informations ».
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Source de la signature pour pouvoir la rééditer (la case « texte » reflète
    # ce qui a été saisi) : mode 'type' (frappe + police) ou 'draw' (tracé souris),
    # avec le texte et la police choisis en mode frappe.
    signature_mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    signature_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature_font: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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

    # Dernière connexion réussie (affichée dans « Gestion des utilisateurs »).
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Visibilité de l'espace propriétaire (lecture seule) ───────────────────
    # Liste de clés de rubriques (cf. core.proprio_sections). Null = non défini.
    # Sur un compte PROPRIÉTAIRE : surcharge individuelle (prioritaire).
    proprio_visibility: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Sur le compte GESTIONNAIRE (racine d'agence) : défaut appliqué à tous ses
    # propriétaires qui n'ont pas de surcharge.
    proprio_visibility_default: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # ── Paiement en ligne par carte (config propre au gestionnaire) ───────────
    # Le gestionnaire renseigne SES clés (Stripe ou SumUp) dans « Mes informations ».
    # Si activé, ses locataires voient le paiement par carte ; sinon il est grisé.
    # Les clés secrètes sont stockées CHIFFRÉES (Fernet, cf. core.crypto).
    card_payments_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    payment_provider: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 'stripe' | 'sumup'
    stripe_secret_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stripe_publishable_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_webhook_secret_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sumup_api_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sumup_merchant_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Devise des encaissements par carte (ISO 4217, ex. EUR). Configurable.
    payment_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", server_default="EUR"
    )

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
