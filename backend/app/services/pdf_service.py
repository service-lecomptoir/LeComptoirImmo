"""
Service de génération PDF via Jinja2 + WeasyPrint.
"""
import io
from pathlib import Path
from typing import Any, Optional

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

    # Identité bailleur du compte gestionnaire = prioritaire. Le nom dépend du type
    # choisi (personne → Prénom Nom ; société → dénomination), via User.bailleur_name.
    _bailleur = getattr(manager, "bailleur_name", None) if manager else None
    if _bailleur:
        bailleur_name = _bailleur
        is_morale = (getattr(manager, "owner_kind", None) == "societe")

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
        # Société + SIRET du mandataire (gestionnaire agissant « pour le compte du bailleur »).
        "mandataire_company": (getattr(manager, "owner_company", "") if manager else "") or "",
        "mandataire_national_id": (getattr(manager, "owner_national_id", "") if manager else "") or "",
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


_CIVILITY_SHORT = {
    "monsieur": "M", "m": "M", "m.": "M", "mr": "M",
    "madame": "Mme", "mme": "Mme",
    "mademoiselle": "Mlle", "mlle": "Mlle",
}


def tenant_reference(tenant) -> str:
    """Identifiant locataire stable et lisible (ex. « 2B12C23A »), dérivé de
    l'identifiant unique du locataire en base (UUID). Vide si pas de locataire."""
    if not tenant:
        return ""
    tid = getattr(tenant, "id", None)
    if not tid:
        return ""
    try:
        return tid.hex[:8].upper()
    except AttributeError:
        return str(tid).replace("-", "")[:8].upper()


def _civil_name(tenant) -> str:
    """Nom du destinataire : civilité + prénom + NOM, en majuscules.
    Ex. « M JOHNNY MONERVILLE ». Vide si pas de locataire."""
    if not tenant:
        return ""
    civ = (getattr(tenant, "civility", "") or "").strip()
    civ = _CIVILITY_SHORT.get(civ.lower(), civ)
    parts = [civ, getattr(tenant, "first_name", "") or "", getattr(tenant, "last_name", "") or ""]
    return " ".join(p for p in parts if p).upper()


_CIVILITY_GREETING = {
    "m": "Monsieur", "m.": "Monsieur", "monsieur": "Monsieur",
    "mme": "Madame", "madame": "Madame",
}


def civility_greeting(tenant) -> str:
    """Formule d'appel personnalisée selon la civilité connue : « Monsieur » /
    « Madame » ; repli neutre « Madame, Monsieur » si inconnue ou « Autre »."""
    civ = ((getattr(tenant, "civility", "") or "").strip().lower()) if tenant else ""
    return _CIVILITY_GREETING.get(civ, "Madame, Monsieur")


async def render_relance_html(db: AsyncSession, payment: Any) -> Optional[str]:
    """Rend la lettre de relance via le template « lettre_relance » de la papeterie
    (modèle par blocs / thème Foncia) du gestionnaire, en réutilisant le moteur de
    blocs commun à tous les documents. Retourne None si aucun template par blocs
    n'est disponible (→ l'appelant retombe sur le modèle .j2 historique)."""
    from datetime import date as _date
    from sqlalchemy import select
    from app.models.document_template import DocumentTemplate
    from app.models.user import User
    from app.services.document_render_service import eur, build_emitter_address
    from app.services.avis_blocks_render_service import render_avis_blocks_html

    lease = getattr(payment, "lease", None)
    property_obj = getattr(lease, "parent_property", None) if lease else None
    gid = getattr(lease, "created_by", None) if lease else None
    if not gid:
        return None

    tmpl = (await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.gestionnaire_id == gid,
            DocumentTemplate.template_type == "lettre_relance",
            DocumentTemplate.is_default.is_(True),
            DocumentTemplate.is_active.is_(True),
        )
    )).scalar_one_or_none()
    if tmpl is None or not getattr(tmpl, "blocks", None):
        return None

    tenant = getattr(payment, "tenant", None)
    _MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
                  "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    _d = _date.today()
    today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"

    user = (await db.execute(select(User).where(User.id == gid))).scalar_one_or_none()
    sender_name = ((user.full_name if user else "") or tmpl.company_name or "")
    sender_addr = (((getattr(user, "full_address", None) or "") if user else "")
                   or tmpl.company_address or "")
    owner_company = (getattr(user, "owner_company", "") or "") if user else ""
    owner_national_id = (getattr(user, "owner_national_id", "") or "") if user else ""

    def _eur(v):
        return f"{eur(v)} €"

    variables = {
        "tenant_name": tenant.full_name if tenant else "",
        "tenant_civil_name": _civil_name(tenant),
        "civility_greeting": civility_greeting(tenant),
        "tenant_email": (getattr(tenant, "email", "") or "") if tenant else "",
        "tenant_phone": (getattr(tenant, "phone", "") or "") if tenant else "",
        "tenant_login": tenant_reference(tenant),
        "tenant_reference": tenant_reference(tenant),
        "property_name": property_obj.name if property_obj else "",
        "property_address": property_obj.full_address_block if property_obj else "",
        "property_street": (getattr(property_obj, "address", "") or "") if property_obj else "",
        "property_city_line": (
            " ".join(p for p in [getattr(property_obj, "zip_code", ""),
                                 getattr(property_obj, "city", "")] if p)
            if property_obj else ""),
        "property_reference": (
            (getattr(property_obj, "reference", "") or getattr(property_obj, "name", ""))
            if property_obj else ""),
        "company_name": sender_name,
        "company_address": build_emitter_address(sender_addr, owner_company, owner_national_id),
        "today_date": today_fr,
        "date": today_fr,
        "period_label": getattr(payment, "period_label", "") or "",
        "period_range": getattr(payment, "period_range_label", "") or getattr(payment, "period_label", "") or "",
        "due_date": payment.due_date.strftime("%d/%m/%Y") if getattr(payment, "due_date", None) else "",
        "amount_due": _eur(getattr(payment, "balance", 0) or 0),
        "apl_amount": _eur(payment.amount_apl) if getattr(payment, "amount_apl", None) else "",
    }
    _logo = getattr(user, "logo_path", None) if user else None
    return render_avis_blocks_html(
        tmpl.blocks, getattr(tmpl, "theme", None), variables,
        line_items=[], logo_path=_logo,
    )


def _add_months(d, m: int):
    """Ajoute `m` mois à une date en bornant le jour au dernier jour du mois cible."""
    import calendar
    from datetime import date as _date
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    return _date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


async def render_plan_apurement_html(db: AsyncSession, payment: Any,
                                     installments: int, first_date) -> Optional[str]:
    """Rend le plan d'apurement via le template « plan_apurement » du gestionnaire,
    avec un échéancier calculé (solde réparti en `installments` mensualités égales
    à partir de `first_date`, la dernière absorbant l'arrondi). Retourne None si
    aucun template par blocs n'est disponible."""
    from datetime import date as _date
    from sqlalchemy import select
    from app.models.document_template import DocumentTemplate
    from app.models.user import User
    from app.services.document_render_service import eur, build_emitter_address
    from app.services.avis_blocks_render_service import render_avis_blocks_html

    lease = getattr(payment, "lease", None)
    property_obj = getattr(lease, "parent_property", None) if lease else None
    gid = getattr(lease, "created_by", None) if lease else None
    if not gid:
        return None
    tmpl = (await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.gestionnaire_id == gid,
            DocumentTemplate.template_type == "plan_apurement",
            DocumentTemplate.is_default.is_(True),
            DocumentTemplate.is_active.is_(True),
        )
    )).scalar_one_or_none()
    if tmpl is None or not getattr(tmpl, "blocks", None):
        return None

    n = max(1, min(int(installments or 1), 36))
    total = round(float(getattr(payment, "balance", 0) or 0), 2)
    base = round(total / n, 2)
    tenant = getattr(payment, "tenant", None)
    _MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
                  "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    _d = _date.today()
    today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"

    def _eur(v):
        return f"{eur(v)} €"

    # Échéancier : mensualités égales, la dernière absorbe l'arrondi.
    line_items = []
    for i in range(n):
        due = _add_months(first_date, i)
        amount = base if i < n - 1 else round(total - base * (n - 1), 2)
        line_items.append({
            "label": f"Échéance {i + 1} du {due.strftime('%d/%m/%Y')}",
            "appele": _eur(amount),
        })

    user = (await db.execute(select(User).where(User.id == gid))).scalar_one_or_none()
    sender_name = ((user.full_name if user else "") or tmpl.company_name or "")
    sender_addr = (((getattr(user, "full_address", None) or "") if user else "")
                   or tmpl.company_address or "")
    owner_company = (getattr(user, "owner_company", "") or "") if user else ""
    owner_national_id = (getattr(user, "owner_national_id", "") or "") if user else ""

    variables = {
        "tenant_name": tenant.full_name if tenant else "",
        "tenant_civil_name": _civil_name(tenant),
        "civility_greeting": civility_greeting(tenant),
        "tenant_email": (getattr(tenant, "email", "") or "") if tenant else "",
        "tenant_phone": (getattr(tenant, "phone", "") or "") if tenant else "",
        "tenant_login": tenant_reference(tenant),
        "tenant_reference": tenant_reference(tenant),
        "property_name": property_obj.name if property_obj else "",
        "property_address": property_obj.full_address_block if property_obj else "",
        "property_street": (getattr(property_obj, "address", "") or "") if property_obj else "",
        "property_city_line": (
            " ".join(p for p in [getattr(property_obj, "zip_code", ""),
                                 getattr(property_obj, "city", "")] if p)
            if property_obj else ""),
        "property_reference": (
            (getattr(property_obj, "reference", "") or getattr(property_obj, "name", ""))
            if property_obj else ""),
        "company_name": sender_name,
        "company_address": build_emitter_address(sender_addr, owner_company, owner_national_id),
        "today_date": today_fr,
        "date": today_fr,
        "period_label": getattr(payment, "period_label", "") or "",
        "period_range": getattr(payment, "period_range_label", "") or getattr(payment, "period_label", "") or "",
        "due_date": payment.due_date.strftime("%d/%m/%Y") if getattr(payment, "due_date", None) else "",
        "amount_due": _eur(total),
        "first_due_date": first_date.strftime("%d/%m/%Y"),
    }
    _logo = getattr(user, "logo_path", None) if user else None
    return render_avis_blocks_html(
        tmpl.blocks, getattr(tmpl, "theme", None), variables,
        line_items=line_items, logo_path=_logo,
    )


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
            "today_date": today_fr,
            "period_range": avis_full.period_range_label,
            "tenant_email": getattr(avis_full.tenant, "email", "") if getattr(avis_full, "tenant", None) else "",
            "tenant_phone": getattr(avis_full.tenant, "phone", "") if getattr(avis_full, "tenant", None) else "",
            # Identifiant locataire : code stable dérivé de l'UUID en base (ex. « 2B12C23A ».
            # tenant_login conservé comme alias rétro-compatible des templates enregistrés.
            "tenant_login": tenant_reference(getattr(avis_full, "tenant", None)),
            "tenant_reference": tenant_reference(getattr(avis_full, "tenant", None)),
            "property_reference": (getattr(property_obj, "reference", "") or
                                   getattr(property_obj, "name", "")) if property_obj else "",
            # Nom du destinataire : civilité + prénom + NOM (majuscules).
            "tenant_civil_name": _civil_name(getattr(avis_full, "tenant", None)),
            "civility_greeting": civility_greeting(getattr(avis_full, "tenant", None)),
            # Adresse du bien décomposée pour le bloc destinataire (lignes séparées).
            "property_address2": (getattr(property_obj, "address2", "") or "") if property_obj else "",
            "property_street": (getattr(property_obj, "address", "") or "") if property_obj else "",
            "property_city_line": (
                " ".join(p for p in [getattr(property_obj, "zip_code", ""),
                                     getattr(property_obj, "city", "")] if p)
                if property_obj else ""),
            "company_address": "",
            "lease_start_date": (
                _lease.start_date.strftime("%d/%m/%Y")
                if _lease is not None and getattr(_lease, "start_date", None) else ""
            ),
        }
        _gid = getattr(_lease_rel, "created_by", None)

        # 1a) Éditeur par blocs (mise en page moderne) : si le template par défaut de
        # l'avis en possède, on rend via le moteur de blocs (prioritaire).
        from app.models.document_template import DocumentTemplate
        from app.models.user import User
        avis_tmpl = None
        if _gid:
            avis_tmpl = (await db.execute(
                select(DocumentTemplate).where(
                    DocumentTemplate.gestionnaire_id == _gid,
                    DocumentTemplate.template_type == "avis_echeance",
                    DocumentTemplate.is_default.is_(True),
                    DocumentTemplate.is_active.is_(True),
                )
            )).scalar_one_or_none()
        if avis_tmpl is not None and getattr(avis_tmpl, "blocks", None):
            from app.services.avis_blocks_render_service import render_avis_blocks_html
            # Nom + adresse de l'expéditeur depuis le profil du gestionnaire.
            sender_name, sender_addr = "", ""
            owner_company, owner_national_id = "", ""
            user = None
            try:
                user = (await db.execute(
                    select(User).where(User.id == _gid)
                )).scalar_one_or_none()
                if user:
                    sender_name = user.full_name or avis_tmpl.company_name or ""
                    sender_addr = (getattr(user, "full_address", None) or "") or avis_tmpl.company_address or ""
                    owner_company = getattr(user, "owner_company", "") or ""
                    owner_national_id = getattr(user, "owner_national_id", "") or ""
            except Exception:
                pass
            if not variables.get("company_name"):
                variables["company_name"] = sender_name
            if not variables.get("company_address"):
                from app.services.document_render_service import build_emitter_address
                variables["company_address"] = build_emitter_address(sender_addr, owner_company, owner_national_id)
            # Le moteur de blocs n'ajoute pas le symbole € (contrairement aux anciens
            # templates HTML) → on le préfixe ici, dans le contexte blocs uniquement.
            def _eur(v):
                return f"{eur(v)} €"
            variables["total_due"] = _eur(_total)
            variables["rent_amount"] = _eur(avis_full.amount_rent)
            variables["charges_amount"] = _eur(avis_full.amount_charges)
            line_items = [
                {"label": "LOYER PRINCIPAL", "appele": _eur(avis_full.amount_rent)},
                {"label": "PROVISION CHARGES", "appele": _eur(avis_full.amount_charges)},
            ]
            if avis_full.amount_apl:
                line_items.append({"label": "AIDE PERSONNELLE AU LOGEMENT",
                                   "appele": "-" + _eur(avis_full.amount_apl)})
            # Logo : UNIQUEMENT celui du profil gestionnaire (« Mes informations »).
            # On n'utilise PAS le logo_path résiduel du modèle (ancien upload par
            # template) → par défaut, pas de logo (emplacement vide réservé).
            _logo = getattr(user, "logo_path", None)
            html = render_avis_blocks_html(
                avis_tmpl.blocks, getattr(avis_tmpl, "theme", None), variables,
                line_items=line_items, logo_path=_logo,
            )
            notice = None
            if _lease_rel is not None:
                from app.services.irl_notice import upcoming_revision_notice, inject_notice
                notice = await upcoming_revision_notice(
                    db, _lease_rel, avis_full.period_year, avis_full.period_month)
                if notice:
                    html = inject_notice(html, notice)
            return html_to_pdf(html)

        custom = await render_saved_document(
            db, template_type="avis_echeance",
            gestionnaire_id=_gid,
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
