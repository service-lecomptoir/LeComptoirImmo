import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_gestionnaire
from app.models.user import User
from app.models.document import EntityType, DocumentType
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services.document_service import DocumentService
from app.utils.file_handler import get_file_path

router = APIRouter(prefix="/documents", tags=["Documents"])


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
