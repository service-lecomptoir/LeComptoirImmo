"""Génération du PDF d'une facture Alice (reportlab)."""
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from app.models.invoice import AliceInvoice

_MONTHS = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

BRAND = "Le Comptoir Immo"
INDIGO = colors.HexColor("#4f46e5")
GRAY = colors.HexColor("#6b7280")
DARK = colors.HexColor("#111827")


def _euro(value: float) -> str:
    return f"{value:,.2f} €".replace(",", " ").replace(".", ",")


def invoice_number(inv: AliceInvoice) -> str:
    return f"{inv.period_year}-{inv.period_month:02d}-{str(inv.id)[:8].upper()}"


def build_invoice_pdf(
    inv: AliceInvoice,
    client_name: str | None,
    client_email: str | None,
) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # ── En-tête marque ────────────────────────────────────────────────
    c.setFillColor(INDIGO)
    c.rect(0, h - 28 * mm, w, 28 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, h - 18 * mm, BRAND)
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 20 * mm, h - 16 * mm, "FACTURE")
    c.drawRightString(w - 20 * mm, h - 21 * mm, f"N° {invoice_number(inv)}")

    y = h - 42 * mm

    # ── Période & date ────────────────────────────────────────────────
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9)
    periode = f"{_MONTHS[inv.period_month]} {inv.period_year}"
    c.drawString(20 * mm, y, "Période facturée")
    c.drawRightString(w - 20 * mm, y, "Date d'émission")
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y - 6 * mm, periode)
    emise = (inv.created_at or datetime.utcnow()).strftime("%d/%m/%Y")
    c.drawRightString(w - 20 * mm, y - 6 * mm, emise)

    # ── Client ────────────────────────────────────────────────────────
    y -= 22 * mm
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, "Facturé à")
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y - 6 * mm, client_name or "—")
    if client_email:
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, y - 11 * mm, client_email)

    # ── Tableau ligne ─────────────────────────────────────────────────
    y -= 26 * mm
    c.setFillColor(colors.HexColor("#f3f4f6"))
    c.rect(20 * mm, y, w - 40 * mm, 9 * mm, fill=1, stroke=0)
    c.setFillColor(GRAY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(24 * mm, y + 2.8 * mm, "DESCRIPTION")
    c.drawRightString(w - 24 * mm, y + 2.8 * mm, "MONTANT")

    y -= 11 * mm
    c.setFillColor(DARK)
    c.setFont("Helvetica", 11)
    formule = inv.plan_name or "Abonnement"
    c.drawString(24 * mm, y, f"Formule {formule} — abonnement mensuel")
    c.drawRightString(w - 24 * mm, y, _euro(float(inv.amount)))

    # ── Total ─────────────────────────────────────────────────────────
    y -= 14 * mm
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.line(20 * mm, y + 8 * mm, w - 20 * mm, y + 8 * mm)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(110 * mm, y, "Total à payer")
    c.drawRightString(w - 24 * mm, y, _euro(float(inv.amount)))

    # ── Statut ────────────────────────────────────────────────────────
    y -= 16 * mm
    paid = inv.status == "paid"
    c.setFillColor(colors.HexColor("#dcfce7") if paid else colors.HexColor("#fef3c7"))
    c.roundRect(20 * mm, y, 40 * mm, 9 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#15803d") if paid else colors.HexColor("#b45309"))
    c.setFont("Helvetica-Bold", 10)
    label = "PAYÉE" if paid else "EN ATTENTE"
    c.drawCentredString(40 * mm, y + 2.8 * mm, label)
    if paid and inv.paid_at:
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9)
        c.drawString(64 * mm, y + 2.8 * mm, f"Réglée le {inv.paid_at.strftime('%d/%m/%Y')}")

    # ── Pied de page ──────────────────────────────────────────────────
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 15 * mm, f"{BRAND} — Facture générée automatiquement par Alice")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
