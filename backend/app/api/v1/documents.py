import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.core.permissions import Role
from app.models.user import User
from app.models.document import EntityType, DocumentType
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services.document_service import DocumentService
from app.utils.file_handler import get_file_path

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=List[DocumentResponse], summary="Liste des documents")
async def list_documents(
    entity_type: Optional[EntityType] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste les documents selon le rôle :
    - Gestionnaire/Admin : tous les documents
    - Locataire : documents liés à son dossier tenant + bail
    - Propriétaire : documents liés à ses biens/logements/baux
    """
    role = Role(current_user.role)

    # ── Locataire ──────────────────────────────────────────────────────────────
    if role == Role.LOCATAIRE:
        from app.models.tenant import Tenant
        from app.models.lease import Lease
        tenant = (await db.execute(
            select(Tenant).where(Tenant.user_id == current_user.id)
        )).scalar_one_or_none()
        if not tenant:
            return []
        leases = (await db.execute(
            select(Lease).where(Lease.tenant_id == tenant.id)
        )).scalars().all()
        entity_ids = [tenant.id] + [l.id for l in leases]
        return await DocumentService.list_for_entities(db, entity_ids, entity_type, limit, skip)

    # ── Propriétaire ───────────────────────────────────────────────────────────
    if role == Role.PROPRIETAIRE:
        from app.models.property import Property
        from app.models.unit import Unit
        from app.models.lease import Lease
        props = (await db.execute(
            select(Property).where(Property.owner_user_id == current_user.id)
        )).scalars().all()
        prop_ids = [p.id for p in props]
        if not prop_ids:
            return []
        units = (await db.execute(
            select(Unit).where(Unit.property_id.in_(prop_ids))
        )).scalars().all()
        unit_ids = [u.id for u in units]
        leases = (await db.execute(
            select(Lease).where(Lease.unit_id.in_(unit_ids))
        )).scalars().all()
        entity_ids = prop_ids + unit_ids + [l.id for l in leases]
        return await DocumentService.list_for_entities(db, entity_ids, entity_type, limit, skip)

    # ── Gestionnaire / Admin ───────────────────────────────────────────────────
    return await DocumentService.list_all(db, entity_type, limit, skip)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Uploader un document",
)
async def upload_document(
    file: UploadFile = File(...),
    entity_type: EntityType = Form(...),
    entity_id: uuid.UUID = Form(...),
    document_type: DocumentType = Form(DocumentType.AUTRE),
    label: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """Upload multipart d'un document lié à une entité (locataire, contrat, logement...)."""
    return await DocumentService.upload(
        db=db,
        file=file,
        entity_type=entity_type,
        entity_id=entity_id,
        document_type=document_type,
        label=label,
        notes=notes,
        uploaded_by=current_user.id,
    )


@router.get("/{doc_id}", response_model=DocumentResponse, summary="Détail d'un document")
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await DocumentService.get_by_id(db, doc_id)


@router.patch("/{doc_id}", response_model=DocumentResponse, summary="Modifier les métadonnées")
async def update_document(
    doc_id: uuid.UUID,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    return await DocumentService.update(db, doc_id, data)


@router.get("/{doc_id}/download", summary="Télécharger un document")
async def download_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = await DocumentService.get_by_id(db, doc_id)
    path = get_file_path(doc.file_path)
    if not path:
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le serveur")
    return FileResponse(
        path=str(path),
        media_type=doc.mime_type,
        filename=doc.file_name,
    )


@router.delete("/{doc_id}", status_code=204, summary="Supprimer un document")
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_gestionnaire),
):
    await DocumentService.delete(db, doc_id)
