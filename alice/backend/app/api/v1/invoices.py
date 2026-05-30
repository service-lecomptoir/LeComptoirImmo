import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.admin import AliceAdmin
from app.models.invoice import AliceInvoice
from app.models.leci import LeciUser
from app.schemas.invoice import InvoiceOut, InvoiceUpdate, GeneratePeriod
from app.core.deps import get_current_alice_admin
from app.services.invoice_service import generate_invoices_for_period, current_period
from app.services.invoice_pdf import build_invoice_pdf, invoice_number
from app.services.email_service import send_invoice_email

router = APIRouter(prefix="/invoices", tags=["Factures"])


async def _serialize(db: AsyncSession, invoices: List[AliceInvoice]) -> List[InvoiceOut]:
    """Enrichit les factures avec le nom / email du gestionnaire."""
    if not invoices:
        return []
    user_ids = {inv.gestionnaire_user_id for inv in invoices}
    users_result = await db.execute(
        select(LeciUser.id, LeciUser.full_name, LeciUser.email).where(LeciUser.id.in_(user_ids))
    )
    users = {row.id: (row.full_name, row.email) for row in users_result.all()}
    out = []
    for inv in invoices:
        name, email = users.get(inv.gestionnaire_user_id, (None, None))
        out.append(
            InvoiceOut(
                id=inv.id,
                gestionnaire_user_id=inv.gestionnaire_user_id,
                gestionnaire_name=name,
                gestionnaire_email=email,
                period_year=inv.period_year,
                period_month=inv.period_month,
                amount=float(inv.amount),
                plan_name=inv.plan_name,
                status=inv.status,
                paid_at=inv.paid_at,
                created_at=inv.created_at,
            )
        )
    return out


@router.get("", response_model=List[InvoiceOut])
async def list_invoices(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Liste les factures d'une période (mois courant par défaut).

    Génère automatiquement les factures du mois courant si elles n'existent pas
    encore — assure une facturation mensuelle sans intervention manuelle."""
    cur_year, cur_month = current_period()
    target_year = year or cur_year
    target_month = month or cur_month

    # Génération paresseuse pour le mois courant
    if target_year == cur_year and target_month == cur_month:
        await generate_invoices_for_period(db, cur_year, cur_month)

    q = select(AliceInvoice).where(
        AliceInvoice.period_year == target_year,
        AliceInvoice.period_month == target_month,
    )
    if status:
        q = q.where(AliceInvoice.status == status)
    q = q.order_by(AliceInvoice.created_at.desc())
    result = await db.execute(q)
    invoices = list(result.scalars().all())
    return await _serialize(db, invoices)


@router.get("/stats")
async def invoices_stats(
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Compteurs globaux (toutes périodes) pour pastilles / synthèse."""
    result = await db.execute(
        select(
            AliceInvoice.status,
            func.count(AliceInvoice.id),
            func.coalesce(func.sum(AliceInvoice.amount), 0),
        ).group_by(AliceInvoice.status)
    )
    counts = {"paid": 0, "unpaid": 0}
    amounts = {"paid": 0.0, "unpaid": 0.0}
    for st, cnt, amt in result.all():
        counts[st] = cnt
        amounts[st] = float(amt)
    return {
        "paid_count": counts["paid"],
        "unpaid_count": counts["unpaid"],
        "paid_amount": round(amounts["paid"], 2),
        "unpaid_amount": round(amounts["unpaid"], 2),
    }


@router.post("/generate", response_model=List[InvoiceOut])
async def generate_invoices(
    data: GeneratePeriod,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Génère manuellement les factures d'une période (mois courant par défaut)."""
    cur_year, cur_month = current_period()
    target_year = data.year or cur_year
    target_month = data.month or cur_month
    if not (1 <= target_month <= 12):
        raise HTTPException(status_code=400, detail="Mois invalide")

    await generate_invoices_for_period(db, target_year, target_month)

    result = await db.execute(
        select(AliceInvoice)
        .where(
            AliceInvoice.period_year == target_year,
            AliceInvoice.period_month == target_month,
        )
        .order_by(AliceInvoice.created_at.desc())
    )
    return await _serialize(db, list(result.scalars().all()))


@router.patch("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Met à jour une facture : statut payé/impayé (toggle) et/ou édition
    complète (montant, formule, période)."""
    result = await db.execute(
        select(AliceInvoice).where(AliceInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    if data.status is not None:
        invoice.status = data.status
        invoice.paid_at = datetime.utcnow() if data.status == "paid" else None
    if data.amount is not None:
        if data.amount < 0:
            raise HTTPException(status_code=400, detail="Montant invalide")
        invoice.amount = data.amount
    if data.plan_name is not None:
        invoice.plan_name = data.plan_name or None
    if data.period_year is not None:
        invoice.period_year = data.period_year
    if data.period_month is not None:
        if not (1 <= data.period_month <= 12):
            raise HTTPException(status_code=400, detail="Mois invalide")
        invoice.period_month = data.period_month

    await db.flush()
    return (await _serialize(db, [invoice]))[0]


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Supprime définitivement une facture."""
    result = await db.execute(
        select(AliceInvoice).where(AliceInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    await db.delete(invoice)
    await db.flush()
    return Response(status_code=204)


@router.post("/{invoice_id}/send-email")
async def send_invoice_by_email(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Envoie la facture (PDF en pièce jointe) par email au gestionnaire.

    Si le SMTP n'est pas configuré, retourne sent=False (envoi simulé)."""
    result = await db.execute(
        select(AliceInvoice).where(AliceInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    user_result = await db.execute(
        select(LeciUser.full_name, LeciUser.email).where(LeciUser.id == invoice.gestionnaire_user_id)
    )
    row = user_result.fetchone()
    if not row or not row.email:
        raise HTTPException(status_code=400, detail="Aucune adresse email pour ce gestionnaire")

    pdf_bytes = build_invoice_pdf(invoice, row.full_name, row.email)
    sent = await send_invoice_email(
        to=row.email,
        client_name=row.full_name or "Client",
        period_year=invoice.period_year,
        period_month=invoice.period_month,
        amount=float(invoice.amount),
        plan_name=invoice.plan_name,
        status=invoice.status,
        pdf_bytes=pdf_bytes,
    )
    if sent:
        return {"sent": True, "recipient": row.email}
    return {
        "sent": False,
        "recipient": row.email,
        "detail": "SMTP non configuré — envoi simulé. Configurez SMTP_HOST pour activer l'envoi réel.",
    }


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    """Télécharge la facture au format PDF."""
    result = await db.execute(
        select(AliceInvoice).where(AliceInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    user_result = await db.execute(
        select(LeciUser.full_name, LeciUser.email).where(LeciUser.id == invoice.gestionnaire_user_id)
    )
    row = user_result.fetchone()
    name = row.full_name if row else None
    email = row.email if row else None

    pdf_bytes = build_invoice_pdf(invoice, name, email)
    filename = f"facture-{invoice_number(invoice)}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
