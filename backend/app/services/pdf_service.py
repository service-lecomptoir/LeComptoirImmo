"""
Service de génération PDF via Jinja2 + WeasyPrint.
"""
import io
import uuid
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


def render_template(template_name: str, context: dict[str, Any]) -> str:
    """Rend un template Jinja2 en HTML."""
    env = _get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**context)


def html_to_pdf(html_content: str) -> bytes:
    """Convertit un HTML en PDF via xhtml2pdf (pure Python, compatible Windows)."""
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise RuntimeError(
            "xhtml2pdf n'est pas installé. "
            "Exécutez : pip install xhtml2pdf"
        )

    pdf_buffer = io.BytesIO()
    result = pisa.CreatePDF(
        html_content,
        dest=pdf_buffer,
        encoding="utf-8",
    )
    if result.err:
        raise RuntimeError(f"Erreur lors de la génération du PDF (code {result.err})")
    return pdf_buffer.getvalue()


def generate_lease_pdf(lease: Any) -> bytes:
    """Génère le PDF d'un contrat de bail."""
    try:
        tenant_names = lease.all_tenant_names
    except Exception:
        tenant_names = lease.tenant.full_name if getattr(lease, "tenant", None) else ""
    html = render_template("lease_bail.html.j2", {"lease": lease, "tenant_names": tenant_names})
    return html_to_pdf(html)


class AvisEcheancePDFService:
    """Génère le PDF d'un avis d'échéance."""

    @staticmethod
    async def generate(db: AsyncSession, avis: Any) -> bytes:
        """
        Génère et retourne les bytes PDF de l'avis d'échéance.
        Charge les relations si besoin (tenant, unit, lease/property).
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.avis_echeance import AvisEcheance
        from app.models.property import Property
        from app.models.lease import Lease

        # Recharger avec toutes les relations nécessaires (+ co-titulaires du bail + bien)
        avis_full = (await db.execute(
            select(AvisEcheance)
            .options(
                selectinload(AvisEcheance.tenant),
                selectinload(AvisEcheance.lease).selectinload(Lease.tenant),
                selectinload(AvisEcheance.lease).selectinload(Lease.co_tenants),
                selectinload(AvisEcheance.lease).selectinload(Lease.parent_property),
            )
            .where(AvisEcheance.id == avis.id)
        )).scalar_one_or_none()

        if not avis_full:
            avis_full = avis

        # Noms de tous les co-titulaires (principal + secondaires)
        tenant_names = ""
        if getattr(avis_full, "lease", None):
            try:
                tenant_names = avis_full.lease.all_tenant_names
            except Exception:
                tenant_names = ""
        if not tenant_names and getattr(avis_full, "tenant", None):
            tenant_names = avis_full.tenant.full_name

        # Récupérer le bien lié au contrat
        property_obj = None
        _lease = getattr(avis_full, "lease", None)
        if _lease is not None:
            property_obj = getattr(_lease, "parent_property", None)
            if property_obj is None and _lease.property_id:
                property_obj = (await db.execute(
                    select(Property).where(Property.id == _lease.property_id)
                )).scalar_one_or_none()

        from datetime import date as _date
        from app.services.template_layout_service import get_layout
        _MONTHS_FR = ["janvier","février","mars","avril","mai","juin",
                      "juillet","août","septembre","octobre","novembre","décembre"]
        _d = _date.today()
        today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"

        html = render_template("avis_echeance.html.j2", {
            "avis": avis_full,
            "property": property_obj,
            "today": today_fr,
            "tenant_names": tenant_names,
            "layout": get_layout(),
        })
        return html_to_pdf(html)
