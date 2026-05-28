"""API Templates — gestion des modèles de documents."""
import uuid
import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
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
    # Admin voit tout ; gestionnaires voient uniquement leurs propres templates
    if not _is_admin(current_user):
        q = q.where(DocumentTemplate.gestionnaire_id == current_user.id)
    q = q.where(DocumentTemplate.is_active.is_(True)).order_by(
        DocumentTemplate.template_type, DocumentTemplate.name
    )
    result = await db.execute(q)
    return list(result.scalars().all())


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
