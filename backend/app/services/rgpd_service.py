"""Service RGPD — droit d'accès (export) et droit à l'effacement (anonymisation).

Principe d'effacement : on ne SUPPRIME pas les lignes comptables (loyers, avis,
quittances) car la loi impose leur conservation. On **pseudonymise** le locataire
(suppression des identifiants directs : nom, e-mail, téléphone, date/lieu de
naissance, employeur, revenus, notes) et on supprime les pièces justificatives
sensibles (documents). L'historique financier reste, mais n'est plus rattaché à
une personne identifiable.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.lease import Lease
from app.models.payment import Payment
from app.models.avis_echeance import AvisEcheance
from app.models.ticket import Ticket
from app.models.document import Document


def _model_to_dict(obj, fields: list[str]) -> dict:
    out = {}
    for f in fields:
        v = getattr(obj, f, None)
        if isinstance(v, (datetime,)):
            v = v.isoformat()
        elif hasattr(v, "isoformat"):       # date
            v = v.isoformat()
        elif isinstance(v, uuid.UUID):
            v = str(v)
        elif v is not None and not isinstance(v, (str, int, float, bool, dict, list)):
            v = float(v)                    # Decimal
        out[f] = v
    return out


async def export_tenant(db: AsyncSession, tenant: Tenant) -> dict:
    """Rassemble TOUTES les données d'un locataire (droit d'accès, article 15)."""
    leases = list((await db.execute(
        select(Lease).where(Lease.tenant_id == tenant.id))).scalars())
    payments = list((await db.execute(
        select(Payment).where(Payment.tenant_id == tenant.id))).scalars())
    avis = list((await db.execute(
        select(AvisEcheance).where(AvisEcheance.tenant_id == tenant.id))).scalars())
    tickets = list((await db.execute(
        select(Ticket).where(Ticket.tenant_id == tenant.id))).scalars())
    documents = list((await db.execute(
        select(Document).where(
            Document.entity_type == "tenant", Document.entity_id == tenant.id))).scalars())

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "identite": _model_to_dict(tenant, [
            "id", "civility", "first_name", "last_name", "company_name", "siret",
            "birth_date", "birth_place", "email", "phone", "phone2", "language",
            "employer", "employer_phone", "monthly_income", "income_source", "notes",
            "anonymized_at", "created_at",
        ]),
        "baux": [_model_to_dict(l, [
            "id", "property_id", "start_date", "end_date", "rent_amount",
            "charges_amount", "deposit_amount", "lease_type", "is_active",
        ]) for l in leases],
        "loyers": [_model_to_dict(p, [
            "id", "period_year", "period_month", "amount_rent", "amount_charges",
            "amount_apl", "amount_due", "amount_paid", "status", "payment_date",
            "payment_method",
        ]) for p in payments],
        "avis_echeance": [_model_to_dict(a, [
            "id", "period_year", "period_month", "amount_total", "status", "kind",
        ]) for a in avis],
        "demarches": [_model_to_dict(t, [
            "id", "title", "status", "created_at",
        ]) for t in tickets],
        "documents": [_model_to_dict(d, [
            "id", "filename", "doc_type", "created_at",
        ]) for d in documents],
    }


async def anonymize_tenant(db: AsyncSession, tenant: Tenant) -> dict:
    """Droit à l'effacement (article 17) : pseudonymise l'identité du locataire et
    supprime ses pièces justificatives. Conserve l'historique comptable (légal).
    Idempotent : ne refait rien si déjà anonymisé. Renvoie un résumé."""
    if tenant.anonymized_at:
        return {"already": True, "anonymized_at": tenant.anonymized_at.isoformat()}

    ref = (str(tenant.id)[:8]).upper()
    tenant.first_name = "Anonymisé"
    tenant.last_name = ref
    tenant.company_name = None
    tenant.siret = None
    tenant.birth_date = None
    tenant.birth_place = None
    tenant.email = None
    tenant.phone = None
    tenant.phone2 = None
    tenant.employer = None
    tenant.employer_phone = None
    tenant.monthly_income = None
    tenant.income_source = None
    tenant.notes = None
    tenant.anonymized_at = datetime.now(timezone.utc)

    # Suppression des pièces justificatives (documents) du locataire.
    docs = list((await db.execute(
        select(Document).where(
            Document.entity_type == "tenant", Document.entity_id == tenant.id))).scalars())
    docs_deleted = 0
    for d in docs:
        await db.delete(d)
        docs_deleted += 1

    await db.flush()
    return {"already": False, "documents_deleted": docs_deleted,
            "anonymized_at": tenant.anonymized_at.isoformat()}
