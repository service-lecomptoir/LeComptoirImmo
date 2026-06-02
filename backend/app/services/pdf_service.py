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


def generate_lease_pdf(lease: Any, owner: Any = None, manager: Any = None, is_mandataire: bool = False) -> bytes:
    """Génère le PDF d'un contrat de bail — logement non meublé (loi 89-462).

    - `owner` : fiche propriétaire du bien (bailleur). Si absent, repli sur les
      champs dénormalisés du bien.
    - `manager` / `is_mandataire` : gestionnaire mandataire (bloc « représenté par »).
    """
    import re as _re
    from datetime import date as _date

    def _fr(d):
        return d.strftime("%d/%m/%Y") if d else ""

    prop = getattr(lease, "parent_property", None)
    tenant = getattr(lease, "tenant", None)
    cots = list(getattr(lease, "co_tenants", []) or [])
    tenant2 = cots[0] if cots else None

    def _split_addr(raw):
        """(rue, 'CP Ville') depuis une adresse libre, normalisée. ('', '') si vide."""
        if not raw:
            return "", ""
        s = " ".join(str(raw).split())
        mm = _re.search(r"\b\d{5}\b", s)
        if mm and mm.start() > 0:
            return s[:mm.start()].rstrip(" ,"), s[mm.start():].strip()
        return s, ""

    if owner is not None:
        is_morale = bool(getattr(owner, "company_name", None))
        bailleur_name = owner.full_name
        bailleur_address = getattr(owner, "address", None) or ""
        bailleur_email = getattr(owner, "email", None) or ""
    else:
        is_morale = False
        bailleur_name = (getattr(prop, "owner_name", None) if prop else "") or ""
        bailleur_address = ""
        bailleur_email = (getattr(prop, "owner_email", None) if prop else "") or ""

    # « Nom et prénom du propriétaire » du compte gestionnaire = bailleur prioritaire
    _owner_name = getattr(manager, "owner_full_name", None) if manager else None
    if _owner_name:
        bailleur_name = _owner_name
        is_morale = False  # nom et prénom d'une personne physique

    bailleur_addr1, bailleur_addr2 = _split_addr(bailleur_address)

    logement_parts = []
    if prop:
        logement_parts = [p for p in [prop.address, getattr(prop, "address2", None)] if p]
    nb_pieces = ""
    if prop and getattr(prop, "typology", None):
        m = _re.search(r"\d+", prop.typology)
        nb_pieces = m.group(0) if m else ""

    try:
        tenant_names = lease.all_tenant_names
    except Exception:
        tenant_names = tenant.full_name if tenant else ""

    ctx = {
        "is_morale": is_morale,
        "bailleur_name": bailleur_name,
        "bailleur_address": bailleur_address,
        "bailleur_addr1": bailleur_addr1,
        "bailleur_addr2": bailleur_addr2,
        "bailleur_email": bailleur_email,
        "is_mandataire": bool(is_mandataire and manager is not None),
        "mandataire_name": (getattr(manager, "full_name", "") if manager else "") or "",
        "mandataire_address": (getattr(manager, "address", "") if manager else "") or "",
        "has_guarantor": bool(getattr(lease, "has_guarantor", False)),
        "guarantor_name": getattr(lease, "guarantor_name", "") or "",
        "tenant_name": tenant.full_name if tenant else "",
        "tenant_email": (getattr(tenant, "email", "") if tenant else "") or "",
        "tenant2_name": tenant2.full_name if tenant2 else "",
        "tenant2_email": (getattr(tenant2, "email", "") if tenant2 else "") or "",
        "logement_address": ", ".join(logement_parts),
        "logement_cp": (prop.zip_code if prop else "") or "",
        "logement_city": (prop.city if prop else "") or "",
        "floor": (prop.floor if prop and prop.floor is not None else ""),
        "surface": (f"{float(prop.area_sqm):.0f}" if prop and prop.area_sqm else ""),
        "nb_pieces": nb_pieces,
        "heating": (getattr(prop, "heating_type", None) if prop else "") or "",
        "dpe": (getattr(prop, "energy_class", None) if prop else "") or "",
        "year_built": (prop.year_built if prop and getattr(prop, "year_built", None) else ""),
        "start_date": _fr(getattr(lease, "start_date", None)),
        "duration_morale": is_morale,
        "rent": f"{float(lease.rent_amount):.2f}",
        "charges": f"{float(lease.charges_amount):.2f}",
        "total": f"{lease.total_monthly:.2f}",
        "payment_day": getattr(lease, "payment_day", 1),
        "deposit": (f"{float(lease.deposit_amount):.2f}" if getattr(lease, "deposit_amount", None) is not None else ""),
        "irl_quarter": getattr(lease, "irl_quarter", None),
        "tenant_names": tenant_names,
        "today": _fr(_date.today()),
    }
    html = render_template("lease_bail.html.j2", ctx)
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

        # Noms de tous les locataires : principal en premier, puis co-titulaires.
        # Chacun est affiché sur SA propre ligne dans le bloc destinataire.
        names: list[str] = []
        if getattr(avis_full, "tenant", None):
            names.append(avis_full.tenant.full_name)
        _lease_rel = getattr(avis_full, "lease", None)
        if _lease_rel is not None:
            try:
                names += [ct.full_name for ct in (_lease_rel.co_tenants or [])]
            except Exception:
                pass
        tenant_names = " & ".join(names)

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
        from app.services.document_render_service import render_saved_document, eur
        _MONTHS_FR = ["janvier","février","mars","avril","mai","juin",
                      "juillet","août","septembre","octobre","novembre","décembre"]
        _d = _date.today()
        today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"
        layout = get_layout()

        # 1) Template ENREGISTRÉ par le gestionnaire (éditeur) si présent…
        _month_label = f"{_MONTHS_FR[avis_full.period_month - 1].capitalize()} {avis_full.period_year}"
        _total = getattr(avis_full, "amount_total", None)
        if _total is None:
            _total = float(avis_full.amount_rent) + float(avis_full.amount_charges)
        variables = {
            "tenant_name": names[0] if names else "",
            "month": _month_label,
            "due_date": avis_full.due_date.strftime("%d/%m/%Y") if avis_full.due_date else "",
            "rent_amount": eur(avis_full.amount_rent),
            "charges_amount": eur(avis_full.amount_charges),
            "apl_amount": eur(avis_full.amount_apl) if avis_full.amount_apl else "",
            "total_due": eur(_total),
            "property_name": property_obj.name if property_obj else "",
            "unit_ref": property_obj.name if property_obj else "",
            "property_address": property_obj.full_address_block if property_obj else "",
            "company_name": "",
            "date": today_fr,
        }
        custom = await render_saved_document(
            db, template_type="avis_echeance",
            gestionnaire_id=getattr(_lease_rel, "created_by", None),
            variables=variables, recipient_lines=names,
            property_address=property_obj.full_address_block if property_obj else "",
            layout=layout,
        )

        # Mention « révision de loyer à venir » (1 mois à l'avance), si applicable.
        notice = None
        if _lease_rel is not None:
            from app.services.irl_notice import upcoming_revision_notice
            notice = await upcoming_revision_notice(
                db, _lease_rel, avis_full.period_year, avis_full.period_month
            )

        if custom:
            if notice:
                from app.services.irl_notice import inject_notice
                custom = inject_notice(custom, notice)
            return html_to_pdf(custom)

        # 2) …sinon, modèle .j2 historique (mise en page complète).
        html = render_template("avis_echeance.html.j2", {
            "avis": avis_full,
            "property": property_obj,
            "today": today_fr,
            "tenant_names": tenant_names,
            "tenant_names_list": names,
            "layout": layout,
        })
        if notice:
            from app.services.irl_notice import inject_notice
            html = inject_notice(html, notice)
        return html_to_pdf(html)
