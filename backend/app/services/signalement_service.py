import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1._isolation import agency_property_ids
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.permissions import Role
from app.models.lease import Lease
from app.models.property import Property
from app.models.signalement import (
    Signalement,
    SignalementSource,
    SignalementStatus,
)
from app.models.tenant import Tenant

CATEGORY_LABELS = {
    "bruit": "Bruit / nuisance sonore",
    "securite": "Sécurité (accès, interphone, éclairage)",
    "proprete": "Propreté des parties communes",
    "ascenseur": "Ascenseur",
    "exterieur": "Espaces extérieurs / parking",
    "degradation": "Dégradation / vandalisme",
    "logement": "Problème dans le logement",  # héritage (anciens signalements)
    "autre": "Autre",
}
URGENCY_LABELS = {"faible": "Faible", "moyen": "Moyen", "urgent": "Urgent"}
STATUS_LABELS = {"nouveau": "Nouveau", "en_cours": "En cours", "resolu": "Résolu", "clos": "Clos"}
SOURCE_LABELS = {"locataire": "Locataire", "gestionnaire": "Gestionnaire", "telematique": "Capteur"}


def _naive_utc(dt: datetime | None) -> datetime:
    """Ramène une date à un datetime NAÏF en UTC (les colonnes sont TIMESTAMP WITHOUT
    TIME ZONE). Le front envoie un ISO avec fuseau → on retire l'offset proprement."""
    if dt is None:
        return datetime.utcnow()
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def enrich(s: Signalement) -> dict:
    prop = getattr(s, "parent_property", None)
    tenant = getattr(s, "tenant", None)
    return {
        "id": s.id,
        "category": s.category,
        "category_label": CATEGORY_LABELS.get(s.category, s.category),
        "urgency": s.urgency,
        "urgency_label": URGENCY_LABELS.get(s.urgency, s.urgency),
        "status": s.status,
        "status_label": STATUS_LABELS.get(s.status, s.status),
        "source": s.source,
        "source_label": SOURCE_LABELS.get(s.source, s.source),
        "title": s.title,
        "description": s.description,
        "occurred_at": s.occurred_at,
        "night_noise": bool(
            s.category == "bruit"
            and s.occurred_at is not None
            and (s.occurred_at.hour >= 22 or s.occurred_at.hour < 7)
        ),
        "photo_url": ("/" + s.photo_path.replace("\\", "/").lstrip("/")) if s.photo_path else None,
        "property_id": s.property_id,
        "property_name": (prop.name if prop else None),
        "property_address": (prop.full_address if prop else None),
        "tenant_id": s.tenant_id,
        "tenant_name": (tenant.full_name if tenant else None),
        "lease_id": s.lease_id,
        "resolution_note": s.resolution_note,
        "resolved_at": s.resolved_at,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


class SignalementService:
    @staticmethod
    async def _tenant_for_user(db: AsyncSession, user_id: uuid.UUID) -> Tenant:
        t = (await db.execute(select(Tenant).where(Tenant.user_id == user_id))).scalar_one_or_none()
        if not t:
            raise BadRequestException("Aucun profil locataire associé à ce compte")
        return t

    @staticmethod
    async def _active_lease(db: AsyncSession, tenant_id: uuid.UUID) -> Lease | None:
        return (
            (
                await db.execute(
                    select(Lease)
                    .options(selectinload(Lease.parent_property))
                    .where(Lease.tenant_id == tenant_id)
                    .order_by(Lease.is_active.desc(), Lease.start_date.desc())
                )
            )
            .scalars()
            .first()
        )

    @staticmethod
    async def _scope_property_ids(db: AsyncSession, user) -> set | None:
        """IDs des biens visibles par le gestionnaire, ou None = tous (admin)."""
        role = Role(user.role)
        if role == Role.ADMIN:
            return None
        if role == Role.GESTIONNAIRE_PROPRIO:
            rows = await db.execute(select(Property.id).where(Property.created_by == user.id))
            return set(rows.scalars().all())
        if role == Role.GESTIONNAIRE:
            return await agency_property_ids(db, user)
        return set()

    @staticmethod
    async def _notify_manager(db: AsyncSession, s: Signalement) -> None:
        """Notifie le gestionnaire responsable du bien (best-effort)."""
        from app.models.notification import Notification, NotificationPriority, NotificationType

        manager_id = None
        if s.property_id:
            prop = await db.get(Property, s.property_id)
            manager_id = getattr(prop, "created_by", None) if prop else None
        if not manager_id and s.tenant_id:
            t = await db.get(Tenant, s.tenant_id)
            manager_id = getattr(t, "created_by", None) if t else None
        if not manager_id:
            return
        prio = (
            NotificationPriority.URGENT
            if s.urgency == "urgent"
            else (
                NotificationPriority.HIGH if s.urgency == "moyen" else NotificationPriority.NORMAL
            )
        )
        cat = CATEGORY_LABELS.get(s.category, s.category)
        db.add(
            Notification(
                title=f"Nouveau signalement : {cat}",
                message=(s.title or s.description or "")[:200],
                notification_type=NotificationType.SYSTEME,
                priority=prio,
                entity_type="signalement",
                entity_id=s.id,
                user_id=manager_id,
            )
        )

    @staticmethod
    async def create_for_locataire(db: AsyncSession, user_id: uuid.UUID, data) -> Signalement:
        tenant = await SignalementService._tenant_for_user(db, user_id)
        lease = await SignalementService._active_lease(db, tenant.id)
        prop = getattr(lease, "parent_property", None) if lease else None
        s = Signalement(
            category=data.category.value if hasattr(data.category, "value") else data.category,
            urgency=data.urgency.value if hasattr(data.urgency, "value") else data.urgency,
            status=SignalementStatus.NOUVEAU.value,
            source=SignalementSource.LOCATAIRE.value,
            title=(data.title or None),
            description=data.description,
            occurred_at=_naive_utc(data.occurred_at),
            property_id=(prop.id if prop else None),
            tenant_id=tenant.id,
            lease_id=(lease.id if lease else None),
            created_by=user_id,
        )
        db.add(s)
        await db.flush()
        await SignalementService._notify_manager(db, s)
        from app.services.signalement_alert_service import SignalementAlertService

        await SignalementAlertService.process_new(db, s)
        return s

    @staticmethod
    async def create_by_manager(db: AsyncSession, user, data) -> Signalement:
        if not data.property_id:
            raise BadRequestException("Le bien (localisation) est requis.")
        scope = await SignalementService._scope_property_ids(db, user)
        if scope is not None and data.property_id not in scope:
            raise BadRequestException("Ce bien n'est pas dans votre périmètre.")
        s = Signalement(
            category=data.category.value if hasattr(data.category, "value") else data.category,
            urgency=data.urgency.value if hasattr(data.urgency, "value") else data.urgency,
            status=SignalementStatus.NOUVEAU.value,
            source=SignalementSource.GESTIONNAIRE.value,
            title=(data.title or None),
            description=data.description,
            occurred_at=_naive_utc(data.occurred_at),
            property_id=data.property_id,
            tenant_id=data.tenant_id,
            lease_id=data.lease_id,
            created_by=user.id,
        )
        db.add(s)
        await db.flush()
        from app.services.signalement_alert_service import SignalementAlertService

        await SignalementAlertService.process_new(db, s)
        return s

    @staticmethod
    async def list_for_locataire(db: AsyncSession, user_id: uuid.UUID) -> list[Signalement]:
        tenant = await SignalementService._tenant_for_user(db, user_id)
        rows = await db.execute(
            select(Signalement)
            .options(selectinload(Signalement.parent_property), selectinload(Signalement.tenant))
            .where(Signalement.tenant_id == tenant.id)
            .order_by(Signalement.created_at.desc())
        )
        return list(rows.scalars().all())

    @staticmethod
    async def list_for_manager(
        db: AsyncSession,
        user,
        *,
        status: str | None = None,
        category: str | None = None,
        urgency: str | None = None,
        property_id: uuid.UUID | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[Signalement], int]:
        scope = await SignalementService._scope_property_ids(db, user)
        q = select(Signalement).options(
            selectinload(Signalement.parent_property), selectinload(Signalement.tenant)
        )
        if scope is not None:
            if not scope:
                return [], 0
            q = q.where(Signalement.property_id.in_(scope))
        if status:
            q = q.where(Signalement.status == status)
        if category:
            q = q.where(Signalement.category == category)
        if urgency:
            q = q.where(Signalement.urgency == urgency)
        if property_id:
            q = q.where(Signalement.property_id == property_id)
        q = q.order_by(Signalement.created_at.desc())
        items = list((await db.execute(q.offset(offset).limit(limit))).scalars().all())
        # total simple (liste bornée à limit élevé) : recompte sur le filtre
        total = len(items) if offset == 0 and len(items) < limit else offset + len(items)
        return items, total

    @staticmethod
    async def get(db: AsyncSession, sig_id: uuid.UUID) -> Signalement:
        s = (
            await db.execute(
                select(Signalement)
                .options(
                    selectinload(Signalement.parent_property), selectinload(Signalement.tenant)
                )
                .where(Signalement.id == sig_id)
            )
        ).scalar_one_or_none()
        if not s:
            raise NotFoundException("Signalement", str(sig_id))
        return s

    @staticmethod
    async def list_alerts(db: AsyncSession, user, *, limit: int = 100) -> list[dict]:
        """Historique des alertes du moteur bruit, dans le périmètre du gestionnaire."""
        from app.models.signalement_alert import SignalementAlert

        labels = {
            "nocturne": "Alerte nocturne",
            "escalade": "Escalade gestionnaire",
            "preventif": "Rappel préventif",
        }
        scope = await SignalementService._scope_property_ids(db, user)
        q = select(SignalementAlert)
        if scope is not None:
            if not scope:
                return []
            q = q.where(SignalementAlert.property_id.in_(scope))
        q = q.order_by(SignalementAlert.created_at.desc()).limit(limit)
        rows = list((await db.execute(q)).scalars().all())
        pids = {a.property_id for a in rows if a.property_id}
        names: dict = {}
        if pids:
            for pid, pname in (
                await db.execute(select(Property.id, Property.name).where(Property.id.in_(pids)))
            ).all():
                names[pid] = pname
        return [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "alert_label": labels.get(a.alert_type, a.alert_type),
                "property_id": a.property_id,
                "property_name": names.get(a.property_id),
                "message": a.message,
                "created_at": a.created_at,
            }
            for a in rows
        ]

    @staticmethod
    async def delete(db: AsyncSession, s: Signalement) -> str | None:
        """Supprime un signalement. Détache d'abord les alertes du moteur bruit qui
        le référençaient (elles restent dans l'historique, sans lien). Renvoie le
        chemin de la photo éventuelle (à supprimer du disque après commit)."""
        from sqlalchemy import update as sa_update

        from app.models.signalement_alert import SignalementAlert

        await db.execute(
            sa_update(SignalementAlert)
            .where(SignalementAlert.signalement_id == s.id)
            .values(signalement_id=None)
        )
        photo = s.photo_path
        await db.delete(s)
        await db.flush()
        return photo

    @staticmethod
    async def assert_manager_scope(db: AsyncSession, user, s: Signalement) -> None:
        scope = await SignalementService._scope_property_ids(db, user)
        if scope is None:
            return
        if s.property_id not in scope:
            raise BadRequestException("Ce signalement n'est pas dans votre périmètre.")

    @staticmethod
    async def update(db: AsyncSession, s: Signalement, data) -> Signalement:
        if data.status is not None:
            s.status = data.status.value if hasattr(data.status, "value") else data.status
            if (
                s.status in (SignalementStatus.RESOLU.value, SignalementStatus.CLOS.value)
                and not s.resolved_at
            ):
                s.resolved_at = datetime.utcnow()
            if s.status not in (SignalementStatus.RESOLU.value, SignalementStatus.CLOS.value):
                s.resolved_at = None
        if data.urgency is not None:
            s.urgency = data.urgency.value if hasattr(data.urgency, "value") else data.urgency
        if data.resolution_note is not None:
            s.resolution_note = data.resolution_note or None
        await db.flush()
        return s

    @staticmethod
    async def problem_properties(db: AsyncSession, user) -> list[dict]:
        """Agrégat « logements à problème » : par bien, nombre de signalements,
        ouverts, et bruit, trié par volume décroissant."""
        scope = await SignalementService._scope_property_ids(db, user)
        # Agrégation en Python (volumes faibles, et évite les différences de cast SQL).
        base = select(Signalement).options(selectinload(Signalement.parent_property))
        if scope is not None:
            if not scope:
                return []
            base = base.where(Signalement.property_id.in_(scope))
        rows = list((await db.execute(base)).scalars().all())
        agg: dict = {}
        for s in rows:
            if not s.property_id:
                continue
            a = agg.setdefault(
                str(s.property_id),
                {
                    "property_id": s.property_id,
                    "property_name": (s.parent_property.name if s.parent_property else "Bien"),
                    "property_address": (
                        s.parent_property.full_address if s.parent_property else None
                    ),
                    "total": 0,
                    "ouverts": 0,
                    "bruit": 0,
                    "urgents": 0,
                },
            )
            a["total"] += 1
            if s.status in ("nouveau", "en_cours"):
                a["ouverts"] += 1
            if s.category == "bruit":
                a["bruit"] += 1
            if s.urgency == "urgent":
                a["urgents"] += 1
        out = list(agg.values())
        out.sort(key=lambda x: (x["ouverts"], x["total"]), reverse=True)
        return out
