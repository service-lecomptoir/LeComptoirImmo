import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_admin, get_current_gestionnaire, get_current_user
from app.core.features import get_plan_name, require_feature
from app.core.permissions import Role
from app.database import get_db
from app.models.email_domain import EmailDomain
from app.models.user import User
from app.schemas.user import (
    AdminPasswordReset,
    UserCreate,
    UserCreateResponse,
    UserPasswordUpdate,
    UserResponse,
    UserRoleUpdate,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

# Rôles que le gestionnaire mandataire peut créer / voir. COMPTABLE = sous-compte
# de gestion en lecture seule (+ encaissement) rattaché à l'agence du créateur.
_GESTIONNAIRE_ALLOWED_ROLES = {Role.PROPRIETAIRE, Role.LOCATAIRE, Role.COMPTABLE}

# PRINCIPE : tout compte de niveau « gestion » (gestionnaire mandataire,
# gestionnaire-propriétaire, admin) est créé EXCLUSIVEMENT depuis Alice (console
# SaaS). L'application LeComptoir Immo ne peut donc jamais créer NI promouvoir
# vers ces rôles — uniquement propriétaire / locataire / lecture / comptable.
_MANAGER_LEVEL_ROLES = {Role.ADMIN, Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO}


async def _gp_tenant_ids(db: AsyncSession, owner_id: uuid.UUID) -> set[str]:
    """Retourne les user_ids des locataires liés aux biens du gestionnaire-propriétaire."""
    from app.models.lease import Lease
    from app.models.property import Property
    from app.models.tenant import Tenant

    prop_ids = list(
        (await db.execute(select(Property.id).where(Property.owner_user_id == owner_id)))
        .scalars()
        .all()
    )
    if not prop_ids:
        return set()

    tenant_table_ids = list(
        (
            await db.execute(
                select(Lease.tenant_id).where(
                    Lease.property_id.in_(prop_ids),
                    Lease.tenant_id.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )
    if not tenant_table_ids:
        return set()

    user_ids = list(
        (
            await db.execute(
                select(Tenant.user_id).where(
                    Tenant.id.in_(tenant_table_ids),
                    Tenant.user_id.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )
    return {str(uid) for uid in user_ids}


async def _require_gp_scope(db: AsyncSession, current_user: User, target_id: uuid.UUID):
    """Pour gestionnaire_proprio : la cible doit être lui-même, un compte qu'il a
    créé (`created_by`), ou un de ses locataires (lié à un de ses biens).

    NB : on s'aligne sur `list_users` (qui montre soi-même + les comptes créés) afin
    qu'un GP puisse modifier/supprimer un compte qu'il vient d'ajouter : y compris
    avant qu'il ne soit rattaché à un bail."""
    if str(target_id) == str(current_user.id):
        return
    target = await db.get(User, target_id)
    if target is not None and str(target.created_by) == str(current_user.id):
        return
    tenant_ids = await _gp_tenant_ids(db, current_user.id)
    if str(target_id) not in tenant_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


@router.get("", response_model=list[UserResponse], summary="Liste des utilisateurs")
async def list_users(
    role: str | None = Query(None, description="Filtrer par rôle (ex: proprietaire, locataire)"),
    unlinked_tenant: bool = Query(
        False,
        description="Exclure les comptes déjà liés à un locataire (pour la création d'un locataire)",
    ),
    unlinked_owner: bool = Query(
        False,
        description="Exclure les comptes déjà liés à une fiche propriétaire (pour la création d'un propriétaire)",
    ),
    owner_id: uuid.UUID | None = Query(
        None,
        description="Fiche propriétaire en cours d'édition : son compte lié reste sélectionnable (les comptes liés aux AUTRES fiches sont exclus)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """
    Retourne la liste des utilisateurs.
    - Admin : tous les utilisateurs
    - Gestionnaire : seulement les propriétaires et locataires
    """
    users = await UserService.list_all(db)

    current_role = Role(current_user.role)

    if current_role == Role.GESTIONNAIRE:
        # Gestionnaire mandataire : comptes gérés (propriétaires, locataires,
        # comptable, lecture…) créés par SON agence. Jamais les comptes de niveau
        # gestionnaire (dont le sien) : il gère le sien dans « Mes informations ».
        from app.api.v1._isolation import agency_member_ids

        members = await agency_member_ids(db, current_user)
        users = [
            u
            for u in users
            if Role(u.role) not in _MANAGER_LEVEL_ROLES
            and u.created_by in members
            and str(u.id) != str(current_user.id)
        ]
    elif current_role == Role.GESTIONNAIRE_PROPRIO:
        # GP : uniquement les locataires qu'il a créés. Pas son propre compte
        # (géré dans « Mes informations »), ni aucun compte de niveau gestionnaire.
        created_rows = (
            (await db.execute(select(User.id).where(User.created_by == current_user.id)))
            .scalars()
            .all()
        )
        created_ids = {str(uid) for uid in created_rows}
        users = [
            u
            for u in users
            if str(u.id) in created_ids
            and Role(u.role) not in _MANAGER_LEVEL_ROLES
            and str(u.id) != str(current_user.id)
        ]

    # Filtre optionnel par rôle
    if role:
        users = [u for u in users if u.role == role]

    # Exclut les comptes déjà rattachés à une fiche locataire (un compte = un locataire)
    if unlinked_tenant:
        from app.models.tenant import Tenant

        linked_rows = (
            (await db.execute(select(Tenant.user_id).where(Tenant.user_id.isnot(None))))
            .scalars()
            .all()
        )
        linked_ids = {str(uid) for uid in linked_rows}
        users = [u for u in users if str(u.id) not in linked_ids]

    # Exclut les comptes déjà rattachés à une fiche propriétaire (un compte = une fiche).
    # En édition (owner_id fourni), le compte de CETTE fiche reste sélectionnable :
    # on n'exclut que les comptes liés aux AUTRES fiches.
    if unlinked_owner:
        from app.models.owner import Owner

        q = select(Owner.user_id).where(Owner.user_id.isnot(None))
        if owner_id is not None:
            q = q.where(Owner.id != owner_id)
        linked_rows = (await db.execute(q)).scalars().all()
        linked_ids = {str(uid) for uid in linked_rows}
        users = [u for u in users if str(u.id) not in linked_ids]

    return users


@router.post("", response_model=UserCreateResponse, status_code=201, summary="Créer un utilisateur")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """
    Crée un nouvel utilisateur.
    - Admin : peut créer n'importe quel rôle
    - Gestionnaire : peut créer uniquement propriétaire ou locataire
    """
    # Les comptes gestionnaire (et admin) ne se créent QUE depuis Alice.
    if Role(data.role) in _MANAGER_LEVEL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les comptes gestionnaire sont créés depuis Alice, pas depuis l'application.",
        )

    current_role = Role(current_user.role)
    if current_role == Role.GESTIONNAIRE:
        if Role(data.role) not in _GESTIONNAIRE_ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un gestionnaire ne peut créer que des comptes propriétaire, locataire ou comptable.",
            )
    elif current_role == Role.GESTIONNAIRE_PROPRIO:
        if Role(data.role) not in {Role.LOCATAIRE, Role.COMPTABLE}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un gestionnaire-propriétaire ne peut créer que des comptes locataire ou comptable.",
            )

    # Règle : le plan Free ne permet pas de créer des comptes locataire.
    if Role(data.role) == Role.LOCATAIRE:
        plan_name = await get_plan_name(db, current_user.id)
        if plan_name and plan_name.strip().lower() == "free":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le plan Free ne permet pas de créer des comptes locataire. Faites évoluer votre formule.",
            )

    # Mot de passe transparent pour le gestionnaire : s'il n'en fournit pas, on
    # en génère un provisoire côté serveur et on l'envoie par e-mail à l'utilisateur.
    # Compte provisoire dans tous les cas → changement forcé à la 1re connexion.
    generated_password: str | None = None
    if not (data.password or "").strip():
        generated_password = _generate_temp_password(12)
        data.password = generated_password

    # Passer current_user.id pour tracer le créateur (isolation GP).
    new_user = await UserService.create(
        db,
        data,
        created_by=current_user.id,
        must_change_password=True,
    )
    from app.services import audit_service

    await audit_service.log(
        db,
        action=audit_service.USER_CREATE,
        user_id=current_user.id,
        user_email=current_user.email,
        entity_type="user",
        entity_id=new_user.id,
        details={"email": new_user.email, "role": new_user.role},
    )

    # Envoi automatique des identifiants (best-effort) quand le mot de passe a été
    # auto-généré : l'utilisateur reçoit son identifiant + mot de passe provisoire.
    credentials_email_sent = False
    if generated_password and (new_user.email or "").strip():
        try:
            from app.services.email_service import send_credentials, set_branding
            from app.services.mail_signature import read_logo

            # Apparence (thème + logo) du gestionnaire créateur.
            _logo, _sub = read_logo(getattr(current_user, "logo_path", None))
            set_branding(
                getattr(current_user, "email_theme", None),
                logo=_logo,
                logo_subtype=_sub,
                brand_name=getattr(current_user, "full_name", None),
            )
            credentials_email_sent = await send_credentials(
                to=new_user.email,
                login=new_user.email,
                password=generated_password,
                full_name=new_user.full_name,
            )
        except Exception as _exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(
                "Envoi identifiants à la création échoué (%s): %s",
                new_user.id,
                _exc,
            )

    resp = UserCreateResponse.model_validate(new_user)
    resp.credentials_email_sent = credentials_email_sent
    return resp


@router.get("/me", response_model=UserResponse, summary="Mon profil")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Retourne le profil de l'utilisateur connecté."""
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Mettre à jour mon profil")
async def update_my_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permet à l'utilisateur connecté de mettre à jour son propre profil (nom, email)."""
    return await UserService.update(db, current_user.id, data)


@router.get("/me/manager", summary="Contact de mon gestionnaire (locataire / propriétaire)")
async def get_my_manager(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Coordonnées de l'agence de rattachement (point de contact) pour un locataire
    ou un propriétaire. Renvoie ``null`` si le compte n'est rattaché à aucune agence."""
    if Role(current_user.role) not in (Role.LOCATAIRE, Role.PROPRIETAIRE):
        return None
    root = await _agency_root_for(db, current_user)
    if not root or root.id == current_user.id:
        return None
    return {
        "full_name": root.full_name,
        "email": root.email,
        "phone": root.phone,
        "address": root.full_address,
    }


@router.get("/{user_id}", response_model=UserResponse, summary="Détail d'un utilisateur")
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    _feat: User = Depends(require_feature("admin")),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    return await UserService.get_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse, summary="Modifier un utilisateur")
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    _feat: User = Depends(require_feature("admin")),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    return await UserService.update(db, user_id, data)


@router.patch("/{user_id}/role", response_model=UserResponse, summary="Changer le rôle")
async def update_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    _feat: User = Depends(require_feature("admin")),
):
    """Modifie le rôle d'un utilisateur. Le passage à un rôle de gestion
    (gestionnaire / gestionnaire-propriétaire / admin) est interdit : ces comptes
    sont gérés exclusivement depuis Alice."""
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Modification de rôle réservée aux administrateurs",
        )
    if Role(data.role) in _MANAGER_LEVEL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le rôle gestionnaire est géré depuis Alice, pas depuis l'application.",
        )
    return await UserService.update_role(db, user_id, data)


@router.patch("/me/password", status_code=204, summary="Changer mon mot de passe")
async def change_my_password(
    data: UserPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permet à l'utilisateur connecté de changer son propre mot de passe."""
    await UserService.update_password(db, current_user, data)


@router.delete("/{user_id}", status_code=204, summary="Supprimer un utilisateur")
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    _feat: User = Depends(require_feature("admin")),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    await UserService.delete(db, user_id)


@router.patch(
    "/{user_id}/password", status_code=204, summary="Réinitialiser le mot de passe d'un utilisateur"
)
async def admin_reset_password(
    user_id: uuid.UUID,
    data: AdminPasswordReset,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    _feat: User = Depends(require_feature("admin")),
):
    """Permet à un gestionnaire/admin de définir un nouveau mot de passe pour un
    utilisateur (ex. locataire), sans connaître l'ancien : comme le ferait le locataire
    depuis son profil. Respecte l'isolation :
    - GP : uniquement les comptes qu'il gère (ses locataires / comptes créés) ;
    - mandataire : uniquement propriétaires et locataires ;
    - admin : tout le monde."""
    role = Role(current_user.role)
    target = await UserService.get_by_id(db, user_id)
    if role == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    elif role == Role.GESTIONNAIRE:
        if Role(target.role) not in _GESTIONNAIRE_ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un gestionnaire ne peut réinitialiser que les comptes propriétaire ou locataire.",
            )
    # Mot de passe défini par le gestionnaire/admin (communiqué à l'utilisateur) :
    # provisoire → changement forcé à la prochaine connexion.
    await UserService.admin_set_password(db, user_id, data.new_password, temporary=True)


def _generate_temp_password(length: int = 10) -> str:
    """Mot de passe temporaire lisible (sans caractères ambigus)."""
    import secrets

    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post(
    "/{user_id}/send-credentials", summary="Envoyer les identifiants de connexion par e-mail"
)
async def send_user_credentials(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    _feat: User = Depends(require_feature("admin")),
):
    """Génère un mot de passe TEMPORAIRE, le pose sur le compte (changement forcé à
    la 1re connexion) et envoie un e-mail à l'utilisateur avec son identifiant et ce
    mot de passe. Le mot de passe actuel n'étant pas récupérable (haché), on en émet
    un nouveau. Respecte l'isolation (GP : ses comptes ; mandataire : proprio/locataire)."""
    role = Role(current_user.role)
    target = await UserService.get_by_id(db, user_id)
    if role == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    elif role == Role.GESTIONNAIRE:
        if Role(target.role) not in _GESTIONNAIRE_ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un gestionnaire ne peut envoyer les identifiants que des comptes propriétaire ou locataire.",
            )
    if not (target.email or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Ce compte n'a pas d'adresse e-mail."
        )

    temp_password = _generate_temp_password()
    await UserService.admin_set_password(db, user_id, temp_password, temporary=True)
    await db.commit()

    email_sent = False
    try:
        from app.services.email_service import send_credentials, set_branding
        from app.services.mail_signature import read_logo

        _logo, _sub = read_logo(getattr(current_user, "logo_path", None))
        set_branding(
            getattr(current_user, "email_theme", None),
            logo=_logo,
            logo_subtype=_sub,
            brand_name=getattr(current_user, "full_name", None),
        )
        email_sent = await send_credentials(
            to=target.email,
            login=target.email,
            password=temp_password,
            full_name=target.full_name,
        )
    except Exception as _exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("Envoi identifiants échoué (%s): %s", user_id, _exc)

    # Audit : ne jamais journaliser le mot de passe.
    from app.services import audit_service

    await audit_service.log(
        db,
        action="user.send_credentials",
        user_id=current_user.id,
        user_email=current_user.email,
        entity_type="user",
        entity_id=target.id,
        details={"to": target.email, "email_sent": email_sent},
    )
    await db.commit()
    return {
        "email_sent": email_sent,
        "to": target.email,
        "detail": (
            "Identifiants envoyés par e-mail."
            if email_sent
            else "Mot de passe temporaire défini, mais e-mail non envoyé (SMTP désactivé ou erreur)."
        ),
    }


# ── Domaines e-mail autorisés ────────────────────────────────────────────────
# Domaines de fournisseurs publics : envoi depuis ces domaines impossible.
_PUBLIC_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "hotmail.fr",
    "outlook.com",
    "outlook.fr",
    "live.com",
    "live.fr",
    "msn.com",
    "yahoo.com",
    "yahoo.fr",
    "ymail.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "aol.com",
    "gmx.com",
    "gmx.fr",
    "proton.me",
    "protonmail.com",
    "orange.fr",
    "wanadoo.fr",
    "free.fr",
    "sfr.fr",
    "laposte.net",
    "bbox.fr",
    "neuf.fr",
    "numericable.fr",
}
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def _normalize_domain(raw: str) -> str:
    d = (raw or "").strip().lower()
    d = d.replace("https://", "").replace("http://", "")
    if "@" in d:
        d = d.split("@")[-1]
    d = d.lstrip("/").split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


class EmailDomainIn(BaseModel):
    domain: str


class EmailDomainOut(BaseModel):
    id: uuid.UUID
    domain: str
    model_config = {"from_attributes": True}


@router.get(
    "/me/email-domains",
    response_model=list[EmailDomainOut],
    summary="Mes domaines e-mail autorisés",
)
async def list_my_email_domains(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        (
            await db.execute(
                select(EmailDomain)
                .where(EmailDomain.user_id == current_user.id)
                .order_by(EmailDomain.created_at)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.post(
    "/me/email-domains",
    response_model=EmailDomainOut,
    status_code=201,
    summary="Ajouter un domaine e-mail",
)
async def add_my_email_domain(
    data: EmailDomainIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = _normalize_domain(data.domain)
    if not _DOMAIN_RE.match(d):
        raise HTTPException(
            status_code=400, detail="Nom de domaine invalide (exemple : mon-agence.fr)."
        )
    if d in _PUBLIC_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'activer l'envoi depuis un domaine d'un fournisseur public "
            "(gmail.com, hotmail.com, yahoo.com, etc.). Utilisez votre propre nom de domaine.",
        )
    existing = (
        await db.execute(
            select(EmailDomain).where(
                EmailDomain.user_id == current_user.id, EmailDomain.domain == d
            )
        )
    ).scalar_one_or_none()
    if existing:
        return EmailDomainOut(id=existing.id, domain=existing.domain)
    obj = EmailDomain(user_id=current_user.id, domain=d)
    db.add(obj)
    await db.flush()
    return EmailDomainOut(id=obj.id, domain=obj.domain)


@router.delete(
    "/me/email-domains/{domain_id}", status_code=204, summary="Supprimer un domaine e-mail"
)
async def delete_my_email_domain(
    domain_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = (
        await db.execute(
            select(EmailDomain).where(
                EmailDomain.id == domain_id, EmailDomain.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Domaine introuvable")
    await db.delete(obj)
    return Response(status_code=204)


# ── Visibilité de l'espace propriétaire (réglée par le gestionnaire) ──────────
class VisibilityUpdate(BaseModel):
    sections: list[str]


async def _agency_root_for(db: AsyncSession, user: User) -> User:
    rid = getattr(user, "agency_id", None) or user.id
    root = await db.get(User, rid)
    return root or user


async def _accessible_proprio(db: AsyncSession, current_user: User, user_id: uuid.UUID) -> User:
    target = await db.get(User, user_id)
    if not target or str(target.role) != "proprietaire":
        raise HTTPException(status_code=404, detail="Compte propriétaire introuvable")
    if Role(current_user.role) == Role.ADMIN:
        return target
    from app.api.v1._isolation import agency_member_ids

    if (
        target.id in await agency_member_ids(db, current_user)
        or target.created_by == current_user.id
    ):
        return target
    raise HTTPException(status_code=403, detail="Ce propriétaire n'est pas dans votre périmètre.")


@router.get("/proprio-visibility/catalog", summary="Rubriques propriétaire disponibles (∩ plan)")
async def proprio_visibility_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    from app.core.features import get_plan_features
    from app.core.proprio_sections import LABELS, PROPRIO_SECTIONS, plan_allowed_keys

    root = await _agency_root_for(db, current_user)
    allowed = set(plan_allowed_keys(await get_plan_features(db, root.id)))
    return {
        "sections": [
            {"key": k, "label": LABELS.get(k, k), "plan_allowed": k in allowed}
            for k, _ in PROPRIO_SECTIONS
        ],
    }


@router.get("/{user_id}/proprio-visibility", summary="Visibilité d'un propriétaire")
async def get_proprio_visibility(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    target = await _accessible_proprio(db, current_user, user_id)
    from app.services.proprio_visibility_service import effective_sections_for

    return {
        "override": target.proprio_visibility,
        "effective": await effective_sections_for(db, target),
        "is_active": target.is_active,
    }


@router.patch(
    "/{user_id}/proprio-visibility",
    summary="Régler la visibilité d'un propriétaire (0 = compte désactivé)",
)
async def set_proprio_visibility(
    user_id: uuid.UUID,
    data: VisibilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    target = await _accessible_proprio(db, current_user, user_id)
    from app.core.features import get_plan_features
    from app.core.proprio_sections import plan_allowed_keys, sanitize
    from app.services.proprio_visibility_service import effective_sections_for

    root = await _agency_root_for(db, current_user)
    allowed = set(plan_allowed_keys(await get_plan_features(db, root.id)))
    secs = [k for k in sanitize(data.sections) if k in allowed]
    target.proprio_visibility = secs
    # Règle « minimum » : 0 rubrique = compte désactivé ; ≥ 1 = (ré)activé.
    target.is_active = len(secs) > 0
    db.add(target)
    await db.commit()
    return {
        "override": secs,
        "is_active": target.is_active,
        "effective": await effective_sections_for(db, target),
    }
