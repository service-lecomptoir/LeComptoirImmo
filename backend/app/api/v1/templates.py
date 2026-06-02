"""API Templates — gestion des modèles de documents."""
import uuid
import os
import shutil
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.models.document_template import DocumentTemplate, TemplateType
from app.schemas.document_template import (
    DocumentTemplateCreate, DocumentTemplateUpdate, DocumentTemplateResponse
)
from app.services.document_template_service import (
    DEFAULT_TEMPLATES, ensure_default_templates,
)

router = APIRouter(prefix="/templates", tags=["Templates"])

UPLOAD_DIR = "uploads/logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _is_admin(current_user) -> bool:
    return Role(current_user.role) == Role.ADMIN


def _check_ownership(tmpl: DocumentTemplate, current_user) -> None:
    """Lève 403 si le template n'appartient pas à l'utilisateur (hors admin)."""
    if _is_admin(current_user):
        return
    if tmpl.gestionnaire_id is None or str(tmpl.gestionnaire_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Ce template ne vous appartient pas")


@router.get("", response_model=List[DocumentTemplateResponse])
async def list_templates(
    template_type: Optional[TemplateType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    q = select(DocumentTemplate)
    if template_type:
        q = q.where(DocumentTemplate.template_type == template_type)
    # Chaque utilisateur (admin inclus) ne voit que SES propres templates : l'admin
    # possède son propre jeu par défaut, et afficher ceux de tous les comptes
    # produisait des doublons apparents (un même type répété par gestionnaire).
    q = q.where(DocumentTemplate.gestionnaire_id == current_user.id)
    q = q.where(DocumentTemplate.is_active.is_(True)).order_by(
        DocumentTemplate.template_type, DocumentTemplate.name
    )
    result = await db.execute(q)
    return list(result.scalars().all())


class TemplatePreviewIn(BaseModel):
    template_type: Optional[str] = None
    content_html: str = ""
    footer_text: str = ""
    header_color: str = "#1E3A5F"
    template_id: Optional[uuid.UUID] = None  # pour récupérer le logo enregistré
    layout: Optional[dict] = None            # surcharge de mise en page (sinon globale)
    blocks: Optional[list] = None            # éditeur par blocs (avis façon Foncia)
    theme: Optional[dict] = None             # thème (palette/police) des blocs


@router.post("/preview")
async def preview_document_pdf(
    data: TemplatePreviewIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    """Génère un PDF d'aperçu du BROUILLON courant, avec la même mise en page que le
    document final (en-tête logo+nom+adresse du profil, corps, pied de page)."""
    from app.services.document_render_service import build_document_html, eur
    from app.services.pdf_service import html_to_pdf
    from app.services.template_layout_service import get_layout

    # Logo : priorité au logo du profil (« Mes informations »), sinon celui du
    # template enregistré qu'on édite.
    logo_path = getattr(current_user, "logo_path", None)
    if not logo_path and data.template_id:
        t = await db.get(DocumentTemplate, data.template_id)
        if t:
            _check_ownership(t, current_user)
            logo_path = getattr(t, "logo_path", None)

    sender_name = getattr(current_user, "full_name", "") or ""
    sender_addr = getattr(current_user, "address", "") or ""

    _MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
                  "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    _d = date.today()
    today_fr = f"{_d.day} {_MONTHS_FR[_d.month - 1]} {_d.year}"

    variables = {
        "tenant_name": "Marie Dupont",
        "tenant_email": "marie.dupont@email.fr",
        "tenant_phone": "06 12 34 56 78",
        "tenant_login": "marie.dupont@email.fr",
        "company_name": sender_name or "Le Comptoir Immo",
        "company_address": sender_addr or "10 rue de la Paix\n75002 Paris",
        "property_name": "Résidence Les Tilleuls",
        "property_reference": "REF-2024-001",
        "unit_ref": "Appartement B12",
        "property_address": "12 avenue des Tilleuls APPART B12\n75001 Paris",
        "rent_amount": eur(800), "charges_amount": eur(80),
        "total_due": eur(880), "amount_paid": eur(880), "apl_amount": eur(0),
        "month": f"{_MONTHS_FR[_d.month - 1].capitalize()} {_d.year}",
        "period_range": "du 01/06/2026 au 30/06/2026",
        "due_date": today_fr, "date": today_fr, "today_date": today_fr,
        "lease_start_date": "01/01/2024",
    }

    # Éditeur par blocs (avis d'échéance « façon Foncia ») : rendu prioritaire.
    if data.blocks is not None:
        from app.services.avis_blocks_render_service import render_avis_blocks_html
        # Le moteur de blocs n'ajoute pas le symbole € → on l'inclut dans les
        # variables/lignes factices de l'aperçu (contexte blocs uniquement).
        block_vars = {**variables,
                      "total_due": f"{eur(880)} €",
                      "rent_amount": f"{eur(800)} €",
                      "charges_amount": f"{eur(80)} €"}
        line_items = [
            {"label": "LOYER PRINCIPAL", "appele": f"{eur(800)} €"},
            {"label": "PROVISION CHARGES", "appele": f"{eur(80)} €"},
        ]
        html = render_avis_blocks_html(
            data.blocks, data.theme, block_vars,
            line_items=line_items, logo_path=logo_path,
        )
        pdf_bytes = html_to_pdf(html)
        return Response(content=pdf_bytes, media_type="application/pdf",
                        headers={"Content-Disposition": 'inline; filename="apercu.pdf"'})

    html = build_document_html(
        header_color=data.header_color, footer_text=data.footer_text,
        content_html=data.content_html, logo_path=logo_path,
        sender_name=sender_name, sender_addr=sender_addr,
        recipient_lines=["Marie Dupont"],
        property_address="12 avenue des Tilleuls APPART B12\n75001 Paris",
        variables=variables, layout=(data.layout or get_layout()),
    )
    pdf_bytes = html_to_pdf(html)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="apercu.pdf"'})


@router.post("/initialize-defaults", status_code=status.HTTP_200_OK)
async def initialize_defaults(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    """Crée les templates par défaut pour l'utilisateur courant s'ils n'existent pas."""
    created = await ensure_default_templates(db, current_user.id)
    await db.commit()
    return {"created": created, "message": f"{created} template(s) par défaut créé(s)"}


@router.post("", response_model=DocumentTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: DocumentTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    if data.is_default:
        await _unset_default(db, data.template_type, current_user.id)

    tmpl = DocumentTemplate(**data.model_dump(), gestionnaire_id=current_user.id)
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/{template_id}", response_model=DocumentTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")
    _check_ownership(tmpl, current_user)
    return tmpl


@router.patch("/{template_id}", response_model=DocumentTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: DocumentTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")
    _check_ownership(tmpl, current_user)

    if data.is_default:
        await _unset_default(db, tmpl.template_type, current_user.id, exclude_id=template_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.post("/{template_id}/upload-logo", response_model=DocumentTemplateResponse)
async def upload_logo(
    template_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")
    _check_ownership(tmpl, current_user)

    if file.content_type not in ("image/png", "image/jpeg", "image/svg+xml", "image/webp"):
        raise HTTPException(status_code=400, detail="Format d'image non supporté (PNG, JPG, SVG, WebP)")

    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"logo_{template_id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    tmpl.logo_path = filepath
    tmpl.logo_url = f"/uploads/logos/{filename}"
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(Role.GESTIONNAIRE)),
):
    tmpl = await db.get(DocumentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template introuvable")
    _check_ownership(tmpl, current_user)
    if tmpl.is_default:
        raise HTTPException(status_code=400, detail="Le template par défaut ne peut pas être supprimé")
    await db.delete(tmpl)
    await db.commit()


async def _unset_default(
    db,
    template_type: TemplateType,
    gestionnaire_id: uuid.UUID,
    exclude_id: uuid.UUID = None,
):
    """Désactive le statut 'défaut' pour les autres templates du même type/gestionnaire."""
    q = select(DocumentTemplate).where(
        DocumentTemplate.template_type == template_type,
        DocumentTemplate.gestionnaire_id == gestionnaire_id,
        DocumentTemplate.is_default.is_(True),
    )
    if exclude_id:
        q = q.where(DocumentTemplate.id != exclude_id)
    result = await db.execute(q)
    for tmpl in result.scalars().all():
        tmpl.is_default = False
    await db.flush()
