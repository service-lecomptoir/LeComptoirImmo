# -*- coding: utf-8 -*-
"""Espace CAF : remplissage des PDF officiels (CERFA) téléversés par le gestionnaire.

Le gestionnaire téléverse le formulaire officiel (attestation de loyer / tiers
payant), associe ses champs aux données de l'application, puis génère le PDF
rempli et signé : affichage, envoi par e-mail au locataire et dépôt dans son
espace. Repli sur le modèle généré (letters.py) tant qu'aucun PDF n'est téléversé.
"""
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_role
from app.core.permissions import Role
from app.core.features import require_feature
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.user import User
from app.models.caf_template import CafTemplate
from app.models.document import EntityType, DocumentType
from app.services.lease_service import LeaseService
from app.api.v1._isolation import assert_lease_access
from app.services import caf_pdf_fill, caf_data
from app.utils.file_handler import save_bytes, get_file_path

router = APIRouter(prefix="/caf", tags=["Espace CAF"])

_DOC_TYPES = ("attestation", "tiers_payant")
_DOC_LABEL = {"attestation": "Attestation de loyer", "tiers_payant": "Formulaire tiers payant"}
_DOC_DOCTYPE = {"attestation": DocumentType.ATTESTATION_CAF, "tiers_payant": DocumentType.ATTESTATION_TIERS}


def _check_doc_type(doc_type: str):
    if doc_type not in _DOC_TYPES:
        raise BadRequestException("Type de document inconnu.")


def _tpl_out(tpl: Optional[CafTemplate], fields: Optional[list] = None) -> dict:
    return {
        "doc_type": tpl.doc_type if tpl else None,
        "has_template": tpl is not None,
        "original_filename": tpl.original_filename if tpl else None,
        "field_map": (tpl.field_map or {}) if tpl else {},
        "fields": fields if fields is not None else (caf_pdf_fill.extract_fields(_read_tpl(tpl)) if tpl else []),
        "sign_page": tpl.sign_page if tpl else 1,
        "sign_x_mm": tpl.sign_x_mm if tpl else 130,
        "sign_y_mm": tpl.sign_y_mm if tpl else 20,
        "sign_w_mm": tpl.sign_w_mm if tpl else 45,
    }


def _read_tpl(tpl: Optional[CafTemplate]) -> bytes:
    if not tpl:
        return b""
    p = get_file_path(tpl.file_path)
    if not p:
        return b""
    try:
        return p.read_bytes()
    except Exception:  # noqa: BLE001
        return b""


async def _get_tpl(db: AsyncSession, gid, doc_type: str) -> Optional[CafTemplate]:
    return (await db.execute(
        select(CafTemplate).where(CafTemplate.gestionnaire_id == gid, CafTemplate.doc_type == doc_type)
    )).scalar_one_or_none()


# ── Données disponibles pour le mapping ───────────────────────────────────────
@router.get("/data-keys", summary="Clés de données disponibles pour le mapping")
async def data_keys(
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    return [{"key": k, "label": lbl} for k, lbl in caf_data.DATA_KEYS]


# ── Modèles CAF (PDF officiels téléversés) ────────────────────────────────────
@router.get("/templates", summary="Modèles CAF du gestionnaire")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    out = {}
    for dt in _DOC_TYPES:
        tpl = await _get_tpl(db, current_user.id, dt)
        out[dt] = _tpl_out(tpl)
    return out


@router.post("/templates/{doc_type}", summary="Téléverser le PDF officiel CAF")
async def upload_template(
    doc_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    _check_doc_type(doc_type)
    content = await file.read()
    if not content[:5] == b"%PDF-":
        raise BadRequestException("Le fichier doit être un PDF.")
    fields = caf_pdf_fill.extract_fields(content)
    file_path, _ = save_bytes(content, "caf_template", str(current_user.id), f"{doc_type}.pdf")
    tpl = await _get_tpl(db, current_user.id, doc_type)
    if tpl is None:
        tpl = CafTemplate(gestionnaire_id=current_user.id, doc_type=doc_type)
        db.add(tpl)
    tpl.file_path = file_path
    tpl.original_filename = file.filename
    # Pré-mapping heuristique des champs non encore associés.
    existing = dict(tpl.field_map or {})
    for f in fields:
        if f not in existing:
            guess = _guess_key(f)
            if guess:
                existing[f] = guess
    tpl.field_map = existing
    await db.commit()
    await db.refresh(tpl)
    return _tpl_out(tpl, fields)


class MappingIn(BaseModel):
    field_map: dict
    sign_page: Optional[int] = None
    sign_x_mm: Optional[int] = None
    sign_y_mm: Optional[int] = None
    sign_w_mm: Optional[int] = None


@router.put("/templates/{doc_type}", summary="Enregistrer le mapping des champs")
async def save_mapping(
    doc_type: str,
    data: MappingIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    _check_doc_type(doc_type)
    tpl = await _get_tpl(db, current_user.id, doc_type)
    if not tpl:
        raise NotFoundException("Modèle CAF", doc_type)
    clean = {str(k): str(v) for k, v in (data.field_map or {}).items()
             if v and str(v) in caf_data.DATA_KEY_SET}
    tpl.field_map = clean
    if data.sign_page is not None:
        tpl.sign_page = max(1, int(data.sign_page))
    if data.sign_x_mm is not None:
        tpl.sign_x_mm = int(data.sign_x_mm)
    if data.sign_y_mm is not None:
        tpl.sign_y_mm = int(data.sign_y_mm)
    if data.sign_w_mm is not None:
        tpl.sign_w_mm = max(10, int(data.sign_w_mm))
    await db.commit()
    await db.refresh(tpl)
    return _tpl_out(tpl)


@router.delete("/templates/{doc_type}", status_code=204, summary="Supprimer le modèle CAF")
async def delete_template(
    doc_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    _check_doc_type(doc_type)
    tpl = await _get_tpl(db, current_user.id, doc_type)
    if tpl:
        await db.delete(tpl)
        await db.commit()


def _guess_key(field_name: str) -> Optional[str]:
    """Heuristique de pré-mapping (le gestionnaire peut corriger ensuite)."""
    n = (field_name or "").lower()
    table = [
        (("siret",), "bailleur_siret"),
        (("mail", "courriel", "email"), "bailleur_email"),
        (("tel", "phone", "téléph"), "bailleur_phone"),
        (("colocataire", "conjoint", "tenant2", "locataire2"), "tenant2_name"),
        (("locataire", "allocataire", "tenant"), "tenant_name"),
        (("bailleur", "proprietaire", "propriétaire", "raison"), "bailleur_name"),
        (("surface", "m2", "m²"), "area_sqm"),
        (("charges comprises", "cc", "total"), "total_tcc"),
        (("charge",), "charges"),
        (("loyer",), "rent_no_charges"),
        (("entree", "entrée", "debut", "début"), "start_date"),
        (("ville", "commune"), "ville"),
        (("adresse", "rue"), "logement_street"),
        (("date", "fait le"), "today"),
    ]
    for keys, val in table:
        if any(k in n for k in keys):
            return val
    return None


# ── Génération / envoi / dépôt ────────────────────────────────────────────────
async def _build_pdf(db: AsyncSession, current_user: User, lease_id: uuid.UUID, doc_type: str) -> tuple[bytes, str]:
    """Retourne (pdf_bytes, filename). Remplit le CERFA téléversé si dispo+mappé,
    sinon repli sur le modèle généré (letters.py)."""
    _check_doc_type(doc_type)
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    await assert_lease_access(db, current_user, lease, write=True)
    tenant = lease.tenant
    prop = lease.parent_property
    from app.utils.filename import doc_filename
    from datetime import date
    fname = doc_filename(
        "attestation_loyer_caf" if doc_type == "attestation" else "formulaire_tiers_payant",
        tenant=tenant.full_name if tenant else None,
        property_name=prop.name if prop else None, year=date.today().year,
    )
    tpl = await _get_tpl(db, current_user.id, doc_type)
    if tpl and tpl.field_map:
        template_bytes = _read_tpl(tpl)
        if template_bytes:
            values_data = await caf_data.build_values(db, current_user, lease)
            # field_map : champ_pdf → clé_donnée  ⇒  champ_pdf → valeur
            pdf_values = {fld: values_data.get(key, "") for fld, key in (tpl.field_map or {}).items()}
            sig = caf_pdf_fill._data_uri_to_png(getattr(current_user, "signature", None))
            pdf = caf_pdf_fill.fill(
                template_bytes, pdf_values, signature_png=sig,
                sign_page=tpl.sign_page, sign_x_mm=tpl.sign_x_mm,
                sign_y_mm=tpl.sign_y_mm, sign_w_mm=tpl.sign_w_mm,
            )
            return pdf, fname
    # Repli : modèle généré existant
    from app.api.v1 import letters as _letters
    if doc_type == "attestation":
        resp = await _letters.attestation_caf(lease_id, db=db, current_user=current_user, _feat=current_user)
    else:
        resp = await _letters.versement_direct_caf(lease_id, db=db, current_user=current_user, _feat=current_user)
    return resp.body, fname


@router.get("/{lease_id}/{doc_type}/pdf", summary="Générer le PDF CAF (rempli + signé)")
async def generate_pdf(
    lease_id: uuid.UUID,
    doc_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    pdf, fname = await _build_pdf(db, current_user, lease_id, doc_type)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fname}"'})


@router.post("/{lease_id}/{doc_type}/deposit", summary="Déposer le PDF dans l'espace locataire")
async def deposit_pdf(
    lease_id: uuid.UUID,
    doc_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    pdf, fname = await _build_pdf(db, current_user, lease_id, doc_type)
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    if not lease.tenant_id:
        raise BadRequestException("Ce bail n'a pas de locataire.")
    from app.services.document_service import DocumentService
    await DocumentService.save_generated(
        db, content=pdf, file_name=fname,
        entity_type=EntityType.TENANT, entity_id=lease.tenant_id,
        document_type=_DOC_DOCTYPE[doc_type], label=_DOC_LABEL[doc_type],
        uploaded_by=current_user.id,
    )
    await db.commit()
    return {"deposited": True}


@router.post("/{lease_id}/{doc_type}/email", summary="Envoyer le PDF CAF au locataire")
async def email_pdf(
    lease_id: uuid.UUID,
    doc_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
    _feat: User = Depends(require_feature("documents_caf")),
):
    pdf, fname = await _build_pdf(db, current_user, lease_id, doc_type)
    lease = await LeaseService.get_by_id(db, lease_id, load_relations=True)
    tenant = lease.tenant
    if not tenant or not (tenant.email or "").strip():
        raise BadRequestException("Le locataire n'a pas d'adresse e-mail.")
    from app.services.email_service import send_email, set_branding
    from app.services.mail_signature import read_logo
    logo, sub = read_logo(getattr(current_user, "logo_path", None))
    set_branding(getattr(current_user, "email_theme", None), logo=logo, logo_subtype=sub,
                 brand_name=getattr(current_user, "full_name", None))
    label = _DOC_LABEL[doc_type]
    html = (f"<p>Bonjour {tenant.full_name},</p>"
            f"<p>Veuillez trouver ci-joint votre <strong>{label.lower()}</strong> pour la CAF.</p>"
            f"<p>Cordialement,<br>Le Comptoir Immo · Service Gestion Locative</p>")
    ok = await send_email(
        to=tenant.email, subject=f"{label} (CAF)",
        html_body=html, attachment_bytes=pdf, attachment_filename=fname,
        cc=getattr(current_user, "email", None),
    )
    return {"email_sent": ok}
