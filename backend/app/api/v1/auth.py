import os
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse
from app.schemas.user import UserMeResponse, ProfileUpdate
from app.services.auth_service import AuthService
from app.services import audit_service
from app.core.exceptions import UnauthorizedException

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=TokenResponse, summary="Connexion utilisateur")
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authentifie un utilisateur et retourne une paire de tokens JWT.

    - **access_token** : valide 30 minutes — à envoyer dans le header `Authorization: Bearer <token>`
    - **refresh_token** : valide 7 jours — à utiliser sur `/auth/refresh` uniquement
    """
    ip = request.client.host if request.client else None
    try:
        user = await AuthService.authenticate(db, data.email, data.password)
    except UnauthorizedException:
        await audit_service.log(
            db, action=audit_service.LOGIN_FAILED,
            user_email=data.email, details={"reason": "auth_failed"}, ip_address=ip,
        )
        raise
    await audit_service.log(
        db, action=audit_service.LOGIN,
        user_id=user.id, user_email=user.email, ip_address=ip,
    )
    return AuthService.generate_tokens(user)


@router.post("/refresh", response_model=AccessTokenResponse, summary="Renouveler l'access token")
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Renouvelle un access token expiré à partir d'un refresh token valide."""
    new_access_token = await AuthService.refresh_access_token(db, data.refresh_token)
    return AccessTokenResponse(access_token=new_access_token)


@router.get("/me", response_model=UserMeResponse, summary="Profil de l'utilisateur connecté")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Retourne les informations de l'utilisateur actuellement authentifié."""
    return current_user


@router.patch("/me", response_model=UserMeResponse, summary="Mettre à jour son profil")
async def update_me(
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Met à jour le profil de l'utilisateur connecté (nom, téléphone, adresse)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


_LOGO_DIR = "uploads/logos"
os.makedirs(_LOGO_DIR, exist_ok=True)


@router.post("/me/logo", response_model=UserMeResponse, summary="Téléverser mon logo")
async def upload_my_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Téléverse le logo du gestionnaire (affiché en en-tête des documents)."""
    if file.content_type not in ("image/png", "image/jpeg", "image/svg+xml", "image/webp"):
        raise HTTPException(status_code=400, detail="Format d'image non supporté (PNG, JPG, SVG, WebP)")
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "png"
    if ext not in ("png", "jpg", "jpeg", "svg", "webp"):
        ext = "png"
    filename = f"user_{current_user.id}.{ext}"
    filepath = os.path.join(_LOGO_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    current_user.logo_path = filepath
    current_user.logo_url = f"/uploads/logos/{filename}"
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.delete("/me/logo", response_model=UserMeResponse, summary="Supprimer mon logo")
async def delete_my_logo(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprime le logo du gestionnaire (l'emplacement reste vide sur les documents)."""
    if current_user.logo_path:
        try:
            os.remove(current_user.logo_path)
        except OSError:
            pass
    current_user.logo_path = None
    current_user.logo_url = None
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user
