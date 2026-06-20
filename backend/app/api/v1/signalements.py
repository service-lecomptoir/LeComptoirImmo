import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.permissions import Role
from app.database import get_db
from app.models.user import User
from app.schemas.signalement import SignalementCreate, SignalementUpdate
from app.services.signalement_service import (
    CATEGORY_LABELS,
    STATUS_LABELS,
    URGENCY_LABELS,
    SignalementService,
    enrich,
)
from app.utils.file_handler import save_file

router = APIRouter(prefix="/signalements", tags=["Signalements"])

_MANAGER_ROLES = (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO, Role.ADMIN)


# ── Locataire ────────────────────────────────────────────────────────────────


@router.get("/mine", summary="Mes signalements (locataire)")
async def my_signalements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await SignalementService.list_for_locataire(db, current_user.id)
    return [enrich(s) for s in items]


@router.post("", status_code=201, summary="Créer un signalement")
async def create_signalement(
    data: SignalementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = Role(current_user.role)
    if role == Role.LOCATAIRE:
        s = await SignalementService.create_for_locataire(db, current_user.id, data)
    elif role in _MANAGER_ROLES:
        s = await SignalementService.create_by_manager(db, current_user, data)
    else:
        raise HTTPException(status_code=403, detail="Rôle non autorisé à signaler.")
    await db.commit()
    await db.refresh(s)
    return {"id": s.id, "status": s.status}


@router.post("/{sig_id}/photo", summary="Joindre une photo à un signalement")
async def attach_photo(
    sig_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = await SignalementService.get(db, sig_id)
    role = Role(current_user.role)
    # Accès : le créateur (locataire) ou un gestionnaire du périmètre.
    if role in _MANAGER_ROLES:
        await SignalementService.assert_manager_scope(db, current_user, s)
    elif str(s.created_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Accès refusé à ce signalement.")
    path, _size = await save_file(file, "signalement", str(s.id))
    s.photo_path = path
    await db.commit()
    await db.refresh(s)
    return {"photo_url": ("/" + path.replace("\\", "/").lstrip("/"))}


# ── Gestionnaire ─────────────────────────────────────────────────────────────


@router.get("/problem-properties", summary="Logements à problème (agrégat)")
async def problem_properties(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    return await SignalementService.problem_properties(db, current_user)


@router.get("/alerts", summary="Historique des alertes bruit")
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    return await SignalementService.list_alerts(db, current_user)


@router.get("/export", summary="Export CSV des signalements")
async def export_csv(
    status: str | None = Query(None),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    items, _ = await SignalementService.list_for_manager(
        db, current_user, status=status, category=category, limit=5000, offset=0
    )
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(
        [
            "Date",
            "Survenu le",
            "Catégorie",
            "Urgence",
            "Statut",
            "Source",
            "Bien",
            "Locataire",
            "Description",
        ]
    )
    for s in items:
        prop = getattr(s, "parent_property", None)
        tenant = getattr(s, "tenant", None)
        w.writerow(
            [
                s.created_at.strftime("%d/%m/%Y %H:%M") if s.created_at else "",
                s.occurred_at.strftime("%d/%m/%Y %H:%M") if s.occurred_at else "",
                CATEGORY_LABELS.get(s.category, s.category),
                URGENCY_LABELS.get(s.urgency, s.urgency),
                STATUS_LABELS.get(s.status, s.status),
                s.source,
                (prop.name if prop else ""),
                (tenant.full_name if tenant else ""),
                (s.description or "").replace("\n", " "),
            ]
        )
    # UTF-16 LE + BOM (FF FE) : seul encodage fiable pour Excel FR (l'UTF-8+BOM est
    # parfois ignoré à l'ouverture par double-clic → accents cassés).
    body = b"\xff\xfe" + buf.getvalue().encode("utf-16-le")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-16le",
        headers={"Content-Disposition": "attachment; filename=signalements.csv"},
    )


@router.get("", summary="Liste des signalements (gestionnaire)")
async def list_signalements(
    status: str | None = Query(None),
    category: str | None = Query(None),
    urgency: str | None = Query(None),
    property_id: uuid.UUID | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    items, total = await SignalementService.list_for_manager(
        db,
        current_user,
        status=status,
        category=category,
        urgency=urgency,
        property_id=property_id,
        limit=limit,
        offset=offset,
    )
    return {"total": total, "items": [enrich(s) for s in items]}


@router.get("/{sig_id}", summary="Détail d'un signalement")
async def get_signalement(
    sig_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = await SignalementService.get(db, sig_id)
    role = Role(current_user.role)
    if role in _MANAGER_ROLES:
        await SignalementService.assert_manager_scope(db, current_user, s)
    elif str(s.created_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Accès refusé à ce signalement.")
    return enrich(s)


@router.patch("/{sig_id}", summary="Mettre à jour un signalement (gestionnaire)")
async def update_signalement(
    sig_id: uuid.UUID,
    data: SignalementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.GESTIONNAIRE)),
):
    s = await SignalementService.get(db, sig_id)
    await SignalementService.assert_manager_scope(db, current_user, s)
    s = await SignalementService.update(db, s, data)
    await db.commit()
    await db.refresh(s)
    s = await SignalementService.get(db, sig_id)
    return enrich(s)
