# -*- coding: utf-8 -*-
"""Génération par BLOCS (mise en page moderne) des documents de la papeterie autres que
l'avis d'échéance : quittance, régularisation de charges, révision de loyer,
décompte de taxes foncières. Réutilise le moteur de blocs et le thème.
"""
from __future__ import annotations

from datetime import date as _date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pdf_service import html_to_pdf, _civil_name, tenant_reference, civility_greeting
from app.services.document_render_service import eur

_MOIS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
            "août", "septembre", "octobre", "novembre", "décembre"]


def _fr_date(d) -> str:
    return f"{d.day} {_MOIS_FR[d.month]} {d.year}" if d else ""


def _eur_sym(v) -> str:
    return f"{eur(v)} €"


def _doc_common_vars(tenant, property_obj, today_fr: str) -> dict:
    """Variables communes (destinataire, bien) — alignées sur l'avis d'échéance."""
    return {
        "tenant_name": tenant.full_name if tenant else "",
        "tenant_civil_name": _civil_name(tenant),
        "civility_greeting": civility_greeting(tenant),
        "tenant_email": (getattr(tenant, "email", "") or "") if tenant else "",
        "tenant_phone": (getattr(tenant, "phone", "") or "") if tenant else "",
        "tenant_login": tenant_reference(tenant),
        "tenant_reference": tenant_reference(tenant),
        "property_name": (getattr(property_obj, "name", "") or "") if property_obj else "",
        "property_reference": ((getattr(property_obj, "reference", "") or
                                getattr(property_obj, "name", "")) if property_obj else ""),
        "property_address": property_obj.full_address_block if property_obj else "",
        "property_address2": (getattr(property_obj, "address2", "") or "") if property_obj else "",
        "property_street": (getattr(property_obj, "address", "") or "") if property_obj else "",
        "property_city_line": (" ".join(p for p in [getattr(property_obj, "zip_code", ""),
                                                    getattr(property_obj, "city", "")] if p)
                               if property_obj else ""),
        "today_date": today_fr,
    }


async def render_blocks_document(db: AsyncSession, gestionnaire_user_id, template_type: str,
                                 variables: dict, line_items=None) -> bytes:
    """Rend un document par blocs : template par défaut du gestionnaire (ses
    blocs/thème) sinon blocs par défaut du type. Logo = profil gestionnaire."""
    from app.models.document_template import DocumentTemplate
    from app.models.user import User
    from app.services.avis_blocks_render_service import (
        render_avis_blocks_html, default_blocks, DEFAULT_THEME)

    tmpl = None
    if gestionnaire_user_id:
        tmpl = (await db.execute(select(DocumentTemplate).where(
            DocumentTemplate.gestionnaire_id == gestionnaire_user_id,
            DocumentTemplate.template_type == template_type,
            DocumentTemplate.is_default.is_(True),
            DocumentTemplate.is_active.is_(True),
        ))).scalar_one_or_none()

    blocks = (getattr(tmpl, "blocks", None) or default_blocks(template_type) or [])
    theme = getattr(tmpl, "theme", None) or DEFAULT_THEME

    logo_path = None
    sender_name, sender_addr = "", ""
    owner_company, owner_national_id = "", ""
    if gestionnaire_user_id:
        user = (await db.execute(select(User).where(User.id == gestionnaire_user_id))).scalar_one_or_none()
        if user:
            logo_path = getattr(user, "logo_path", None)
            sender_name = user.full_name or ""
            sender_addr = getattr(user, "address", "") or ""
            owner_company = getattr(user, "owner_company", "") or ""
            owner_national_id = getattr(user, "owner_national_id", "") or ""

    from app.services.document_render_service import build_emitter_address
    variables = dict(variables)
    if not variables.get("company_name"):
        variables["company_name"] = sender_name
    if not variables.get("company_address"):
        # Émetteur enrichi : Société + « SIRET : … » + adresse (sidebar de l'en-tête).
        variables["company_address"] = build_emitter_address(sender_addr, owner_company, owner_national_id)

    html = render_avis_blocks_html(blocks, theme, variables, line_items=line_items, logo_path=logo_path)
    return html_to_pdf(html)


async def _load_tenant_property(db: AsyncSession, lease):
    from app.models.property import Property
    from app.models.tenant import Tenant
    tenant = await db.get(Tenant, lease.tenant_id) if lease is not None else None
    property_obj = None
    if lease is not None and getattr(lease, "property_id", None):
        property_obj = await db.get(Property, lease.property_id)
    return tenant, property_obj


class ChargeRegularizationPDFService:
    @staticmethod
    async def generate(db: AsyncSession, reg) -> bytes:
        from app.models.lease import Lease
        lease = await db.get(Lease, reg.lease_id)
        tenant, property_obj = await _load_tenant_property(db, lease)
        period = (f"du {reg.period_start.strftime('%d/%m/%Y')} "
                  f"au {reg.period_end.strftime('%d/%m/%Y')}")
        balance = float(reg.balance)
        result_label = "Montant en votre faveur" if balance >= 0 else "Complément à régler"
        v = _doc_common_vars(tenant, property_obj, _fr_date(_date.today()))
        v.update({
            "period_range": period,
            "regul_real": _eur_sym(reg.real_total),
            "regul_quote_part": _eur_sym(reg.real_total),
            "regul_provisions": _eur_sym(reg.provisions_total),
            "regul_result_label": result_label,
            "regul_result_amount": _eur_sym(abs(balance)),
        })
        return await render_blocks_document(db, getattr(lease, "created_by", None),
                                            "regularisation_charges", v)


class RevisionLoyerPDFService:
    @staticmethod
    async def generate(db: AsyncSession, lease) -> bytes:
        from app.services.irl_service import IrlService
        tenant, property_obj = await _load_tenant_property(db, lease)
        quarter = lease.irl_quarter
        base = float(lease.irl_base_index) if lease.irl_base_index else None
        latest = await IrlService.get_latest_for_quarter(db, quarter) if quarter else None
        old_rent = float(lease.rent_amount)
        coeff = new_rent = None
        if base and base > 0 and latest is not None:
            coeff = float(latest.value) / base
            new_rent = round(old_rent * coeff, 2)
        ref = lease.last_revision_date or lease.start_date
        eff = None
        if ref:
            try:
                eff = ref.replace(year=ref.year + 1)
            except ValueError:
                eff = ref.replace(year=ref.year + 1, day=28)

        def _idx(x):
            return f"{float(x):.2f}".replace(".", ",")

        v = _doc_common_vars(tenant, property_obj, _fr_date(_date.today()))
        v.update({
            "period_range": "",
            "rev_old_rent": _eur_sym(old_rent),
            "rev_old_index": _idx(base) if base else "—",
            "rev_new_index": _idx(latest.value) if latest else "—",
            "rev_quarter": str(quarter or ""),
            "rev_old_index_year": str((latest.year - 1) if latest else ""),
            "rev_new_index_year": str(latest.year if latest else ""),
            "rev_coeff": (f"{_idx(latest.value)} / {_idx(base)} = "
                          f"{coeff:.8f}".replace(".", ",")) if coeff else "—",
            "rev_new_rent": _eur_sym(new_rent) if new_rent is not None else "—",
            "rev_effective_date": _fr_date(eff),
        })
        return await render_blocks_document(db, getattr(lease, "created_by", None),
                                            "revision_loyer", v)


class TaxesFoncieresPDFService:
    @staticmethod
    async def generate(db: AsyncSession, lease, year: int, teom_amount: float) -> bytes:
        tenant, property_obj = await _load_tenant_property(db, lease)
        y0, y1 = _date(year, 1, 1), _date(year, 12, 31)
        total_days = (y1 - y0).days + 1
        start = max(lease.start_date, y0) if getattr(lease, "start_date", None) else y0
        end = min(lease.end_date, y1) if getattr(lease, "end_date", None) else y1
        days = (end - start).days + 1 if end >= start else 0
        quote = round(float(teom_amount) * days / total_days, 2) if total_days else 0.0
        v = _doc_common_vars(tenant, property_obj, _fr_date(_date.today()))
        v.update({
            "period_range": f"du 01/01/{year} au 31/12/{year}",
            "tax_label": f"TAXE ENLÈVEMENT O.M. {year}",
            "tax_total": _eur_sym(teom_amount),
            "tax_days": str(days),
            "tax_quote_part": _eur_sym(quote),
            "tax_provisions": _eur_sym(0),
        })
        return await render_blocks_document(db, getattr(lease, "created_by", None),
                                            "taxes_foncieres", v)
