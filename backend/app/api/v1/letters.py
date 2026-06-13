"""
API de génération de lettres et documents PDF.
"""
import re
import uuid
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import Role
from app.api.deps import require_role
from app.api.v1._isolation import assert_payment_access, assert_lease_access
from app.models.user import User
from app.models.owner import Owner
from app.core.features import require_feature
from app.services.lease_service import LeaseService
from app.services.payment_service import PaymentService
from app.services.pdf_service import render_template, html_to_pdf, render_relance_html
from app.services.document_service import DocumentService
from app.models.document import EntityType, DocumentType
from app.core.exceptions import BadRequestException

router = APIRouter(prefix="/letters", tags=["Letters"])


async def _save_to_tenant_docs(db, payment, current_user, pdf: bytes, filename: str, label: str):
    """Ajoute un courrier généré dans « Mes documents » du locataire (non bloquant :
    une erreur de stockage ne doit jamais empêcher le téléchargement)."""
    tenant_id = getattr(payment, "tenant_id", None)
    if not tenant_id:
        return
    try:
        await DocumentService.save_generated(
            db, content=pdf, file_name=filename,
            entity_type=EntityType.TENANT, entity_id=tenant_id,
            document_type=DocumentType.AUTRE, label=label,
            uploaded_by=current_user.id,
        )
    except Exception:
        pass

LEASE_TYPE_LABELS = {
    "vide": "Location vide (loi du 6 juillet 1989)",
    "meuble": "Location meublée",
    "mobilite": "Bail mobilité",
    "commercial": "Bail commercial",
}

MONTHS_FR = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _today_str() -> str:
    d = date.today()
    return f"{d.day} {MONTHS_FR[d.month]} {d.year}"


def _split_address(raw):
    """Coupe une adresse libre en (rue, 'CP Ville') devant le 1er code postal à
    5 chiffres. Normalise les espaces/sauts de ligne. Retourne ('', '') si vide."""
    if not raw:
        return "", ""
    s = " ".join(str(raw).split())
    m = re.search(r"\b\d{5}\b", s)
    if m and m.start() > 0:
        return s[:m.start()].rstrip(" ,"), s[m.start():].strip()
    return s, ""


def _split_address_parts(raw):
    """(rue, code_postal, commune) depuis une adresse libre. CP = 1er groupe de 5 chiffres."""
    if not raw:
        return "", "", ""
    s = " ".join(str(raw).split())
    m = re.search(r"\b(\d{5})\b", s)
    if m:
        return s[:m.start()].rstrip(" ,"), m.group(1), s[m.end():].lstrip(" ,").strip()
    return s, "", ""


@router.get("/relance/{payment_id}")
async def lettre_relance(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Génère une lettre de relance pour un loyer impayé."""
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, payment, write=True)
    if payment.status not in ("pending", "partial", "late"):
        raise BadRequestException("Ce loyer ne nécessite pas de relance")

    property_obj = payment.lease.parent_property if payment.lease else None
    apl_info = bool(payment.amount_apl)

    ctx = {
        "property_name": property_obj.name if property_obj else "Le bailleur",
        "property_address": property_obj.full_address if property_obj else "",
        "city": (property_obj.city if property_obj else ""),
        "tenant_name": payment.tenant.full_name if payment.tenant else "",
        "period_label": payment.period_label,
        "due_date": payment.due_date.strftime("%d/%m/%Y"),
        "amount_due": f"{payment.balance:.2f}",
        "apl_info": apl_info,
        "apl_amount": f"{float(payment.amount_apl):.2f}" if payment.amount_apl else "0.00",
        "today": _today_str(),
        "signature_uri": (getattr(current_user, "signature", None) or ""),
    }

    # Modèle de la papeterie (blocs / thème Foncia) en priorité ; repli .j2 sinon.
    html = await render_relance_html(db, payment)
    if not html:
        html = render_template("lettre_relance.html.j2", ctx)
    pdf = html_to_pdf(html)

    from app.utils.filename import doc_filename
    filename = doc_filename(
        "relance",
        tenant=payment.tenant.full_name if payment.tenant else None,
        property_name=property_obj.name if property_obj else None,
        month=payment.period_month,
        year=payment.period_year,
    )
    await _save_to_tenant_docs(db, payment, current_user, pdf, filename,
                               f"Lettre de relance · {payment.period_label}")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/plan-apurement/{payment_id}")
async def plan_apurement(
    payment_id: uuid.UUID,
    installments: int = 3,
    first_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    """Génère un plan d'apurement (échéancier) pour un loyer impayé."""
    payment = await PaymentService.get_by_id(db, payment_id, load_relations=True)
    await assert_payment_access(db, current_user, payment, write=True)
    if payment.status not in ("pending", "partial", "late"):
        raise BadRequestException("Ce loyer ne nécessite pas de plan d'apurement")

    # Première échéance : fournie (YYYY-MM-DD) ou 1er du mois prochain par défaut.
    if first_date:
        try:
            fd = date.fromisoformat(first_date)
        except ValueError:
            raise BadRequestException("Date de première échéance invalide")
    else:
        d = date.today()
        fd = date(d.year + (1 if d.month == 12 else 0),
                  1 if d.month == 12 else d.month + 1, 1)

    from app.services.pdf_service import render_plan_apurement_html
    html = await render_plan_apurement_html(db, payment, installments, fd)
    if not html:
        raise BadRequestException("Modèle de plan d'apurement indisponible")
    pdf = html_to_pdf(html)

    from app.utils.filename import doc_filename
    property_obj = payment.lease.parent_property if payment.lease else None
    filename = doc_filename(
        "plan_apurement",
        tenant=payment.tenant.full_name if payment.tenant else None,
        property_name=property_obj.name if property_obj else None,
        month=payment.period_month, year=payment.period_year,
    )
    await _save_to_tenant_docs(db, payment, current_user, pdf, filename,
                               f"Plan d'apurement · {payment.period_label}")
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/attestation-caf/{lease_id}")
async def attestation_caf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    """Génère une attestation de loyer pour la CAF."""
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, current_user, lease, write=True)

    tenant = lease.tenant
    prop = lease.parent_property
    today = date.today()

    # Bailleur = fiche propriétaire du bien (sinon copie dénormalisée, sinon utilisateur)
    owner = None
    if prop and prop.owner_id:
        owner = (await db.execute(select(Owner).where(Owner.id == prop.owner_id))).scalar_one_or_none()

    co_tenants = list(lease.co_tenants or [])
    tenant2 = co_tenants[0] if co_tenants else None
    nb_coloc = 1 + len(co_tenants)
    is_coloc = nb_coloc > 1
    is_furnished = str(lease.lease_type) == "meuble"
    sd = lease.start_date

    # Adresse bailleur (texte libre) → coupée en « rue » / « CP Ville » devant le code postal
    bailleur_addr1, bailleur_addr2 = _split_address(owner.full_address if owner else None)
    # Adresse logement → rue (champ structuré) puis « CP Ville »
    logement_street = (prop.address if prop else "") or ""
    logement_cpville = " ".join(p for p in [(prop.zip_code if prop else ""), (prop.city if prop else "")] if p).strip()

    ctx = {
        "bailleur_name": getattr(current_user, "owner_full_name", None) or (owner.full_name if owner else None) or (prop.owner_name if prop else None) or current_user.full_name,
        "bailleur_addr1": bailleur_addr1,
        "bailleur_addr2": bailleur_addr2,
        "bailleur_phone": (owner.phone if owner else None) or (prop.owner_phone if prop else None) or getattr(current_user, "phone", None) or "",
        "bailleur_email": (owner.email if owner else None) or (prop.owner_email if prop else None) or current_user.email,
        "bailleur_siret": (owner.national_id if owner else None) or "",
        "tenant_name": tenant.full_name if tenant else "",
        "tenant2_name": tenant2.full_name if tenant2 else None,
        "start_date": sd.strftime("%d/%m/%Y"),
        "logement_street": logement_street,
        "logement_cpville": logement_cpville,
        "ville": prop.city if prop and prop.city else "",
        "is_chambre": False,
        "area_sqm": f"{float(prop.area_sqm):.0f}" if prop and prop.area_sqm else None,
        "is_coloc": is_coloc,
        "nb_coloc": nb_coloc,
        "is_furnished": is_furnished,
        "month_entry": f"{MONTHS_FR[sd.month]} {sd.year}",
        "july_year": today.year,
        "rent_no_charges": f"{float(lease.rent_amount):.2f}",
        "charges": f"{float(lease.charges_amount):.2f}",
        "total_tcc": f"{lease.total_monthly:.2f}",
        "a_jour": True,
        "decence": True,
        "today": _today_str(),
        # Mandataire (gestionnaire) signataire « pour le compte du bailleur ».
        "mandataire_company": getattr(current_user, "owner_company", "") or "",
        "mandataire_national_id": getattr(current_user, "owner_national_id", "") or "",
        "signature_uri": (getattr(current_user, "signature", None) or ""),
    }

    html = render_template("attestation_caf.html.j2", ctx)
    pdf = html_to_pdf(html)

    from app.utils.filename import doc_filename
    filename = doc_filename(
        "attestation_caf",
        tenant=tenant.full_name if tenant else None,
        property_name=prop.name if prop else None,
        year=today.year,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/versement-direct/{lease_id}")
async def versement_direct_caf(
    lease_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    """Génère la demande de versement direct de l'aide au logement (CERFA 11362*04)."""
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, current_user, lease, write=True)
    tenant = lease.tenant
    prop = lease.parent_property
    today = date.today()

    owner = None
    if prop and prop.owner_id:
        owner = (await db.execute(select(Owner).where(Owner.id == prop.owner_id))).scalar_one_or_none()

    # Bailleur : c'est le « Nom et prénom du propriétaire » du profil (owner_full_name),
    # source de vérité commune au bail, à l'attestation de loyer et au tiers payant —
    # PAS le nom de la résidence (current_user.full_name) ni la raison sociale de fiche.
    # Le CERFA a deux cases distinctes : on scinde « Nom et prénom » → 1er mot = Nom,
    # le reste = Prénom (le bailleur vérifie/corrige avant signature).
    prof_name = (getattr(current_user, "owner_full_name", None) or "").strip()
    if prof_name:
        _toks = prof_name.split()
        bailleur_nom = _toks[0]
        bailleur_prenom = " ".join(_toks[1:])
    elif owner and owner.company_name:
        bailleur_nom, bailleur_prenom = owner.company_name, ""
    elif owner and (owner.last_name or owner.first_name):
        bailleur_nom, bailleur_prenom = owner.last_name or "", owner.first_name or ""
    else:
        bailleur_nom, bailleur_prenom = current_user.full_name, ""
    b_rue, b_cp, b_commune = _split_address_parts(owner.full_address if owner else None)

    ctx = {
        "bailleur_nom": bailleur_nom,
        "bailleur_prenom": bailleur_prenom,
        "bailleur_rue": b_rue,
        "bailleur_cp": b_cp,
        "bailleur_commune": b_commune,
        "bailleur_phone": (owner.phone if owner else None) or (prop.owner_phone if prop else None) or getattr(current_user, "phone", None) or "",
        "bailleur_email": (owner.email if owner else None) or (prop.owner_email if prop else None) or current_user.email,
        "bailleur_siret": (owner.national_id if owner else None) or "",
        # Allocataire = locataire ; adresse = logement
        "alloc_nom": tenant.last_name if tenant else "",
        "alloc_prenom": tenant.first_name if tenant else "",
        "alloc_rue": (prop.address if prop else "") or "",
        "alloc_cp": (prop.zip_code if prop else "") or "",
        "alloc_commune": (prop.city if prop else "") or "",
        "alloc_secu": (tenant.national_id if tenant else "") or "",
        "ville": prop.city if prop and prop.city else "",
        "today": _today_str(),
        "signature_uri": (getattr(current_user, "signature", None) or ""),
    }

    html = render_template("versement_direct_caf.html.j2", ctx)
    pdf = html_to_pdf(html)

    from app.utils.filename import doc_filename
    filename = doc_filename(
        "versement_direct_caf",
        tenant=tenant.full_name if tenant else None,
        property_name=prop.name if prop else None,
        year=today.year,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
