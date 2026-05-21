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
    """Convertit un HTML en PDF via WeasyPrint."""
    try:
        from weasyprint import HTML as WeasyHTML
        pdf_buffer = io.BytesIO()
        WeasyHTML(string=html_content).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()
    except ImportError:
        raise RuntimeError(
            "WeasyPrint n'est pas installé. "
            "Exécutez : pip install weasyprint"
        )


def generate_lease_pdf(lease: Any) -> bytes:
    """Génère le PDF d'un contrat de bail."""
    html = render_template("lease_bail.html.j2", {"lease": lease})
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
        from app.models.unit import Unit
        from app.models.property import Property

        # Recharger avec toutes les relations nécessaires
        avis_full = (await db.execute(
            select(AvisEcheance)
            .options(
                selectinload(AvisEcheance.tenant),
                selectinload(AvisEcheance.unit),
                selectinload(AvisEcheance.lease),
            )
            .where(AvisEcheance.id == avis.id)
        )).scalar_one_or_none()

        if not avis_full:
            avis_full = avis

        # Récupérer le bien lié au logement
        property_obj = None
        if avis_full.unit and avis_full.unit.property_id:
            property_obj = (await db.execute(
                select(Property).where(Property.id == avis_full.unit.property_id)
            )).scalar_one_or_none()

        html = render_template("avis_echeance.html.j2", {
            "avis": avis_full,
            "property": property_obj,
        })
        return html_to_pdf(html)
