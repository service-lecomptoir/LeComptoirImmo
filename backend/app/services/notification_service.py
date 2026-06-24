import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.schemas.notification import NotificationCreate


class NotificationService:
    @staticmethod
    async def create(db: AsyncSession, data: NotificationCreate) -> Notification:
        notif = Notification(**data.model_dump())
        db.add(notif)
        await db.flush()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.is_read == False,
                Notification.user_id == user_id,
            )
        )
        return result.scalar_one()

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> tuple[list[Notification], int, int]:
        """Returns (items, total, unread_count). Strictement scopé au destinataire."""
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)

        total_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_q)).scalar_one()

        unread_q = select(func.count(Notification.id)).where(
            Notification.is_read == False,
            Notification.user_id == user_id,
        )
        unread_count = (await db.execute(unread_q)).scalar_one()

        items = (
            (await db.execute(query.order_by(Notification.created_at.desc()).limit(limit)))
            .scalars()
            .all()
        )

        return list(items), total, unread_count

    @staticmethod
    async def mark_read(
        db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification:
        """Marque une notification lue — uniquement si elle appartient à l'utilisateur."""
        notif = await db.get(Notification, notification_id)
        if not notif or notif.user_id != user_id:
            raise NotFoundException("Notification introuvable")
        notif.is_read = True
        notif.read_at = datetime.utcnow()
        await db.flush()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(Notification).where(
                Notification.is_read == False,
                Notification.user_id == user_id,
            )
        )
        notifs = result.scalars().all()
        now = datetime.utcnow()
        for n in notifs:
            n.is_read = True
            n.read_at = now
        await db.flush()
        return len(notifs)

    # ── Génération d'alertes automatiques ─────────────────────────────────────

    @staticmethod
    async def _recipients_for_lease(db: AsyncSession, lease) -> set:
        """Destinataires d'une alerte liée à un bail : gestionnaire(s) + propriétaire.

        Strictement les comptes concernés par le bien (jamais de diffusion globale)."""
        from app.models.property import Property

        recipients: set = set()
        if getattr(lease, "created_by", None):
            recipients.add(lease.created_by)
        prop = await db.get(Property, lease.property_id) if lease.property_id else None
        if prop:
            if getattr(prop, "created_by", None):
                recipients.add(prop.created_by)
            if getattr(prop, "owner_user_id", None):
                recipients.add(prop.owner_user_id)
        recipients.discard(None)
        return recipients

    @staticmethod
    async def _alert_exists(db, ntype, entity_type, entity_id, user_id) -> bool:
        return (
            await db.execute(
                select(Notification.id).where(
                    Notification.notification_type == ntype,
                    Notification.entity_type == entity_type,
                    Notification.entity_id == entity_id,
                    Notification.user_id == user_id,
                )
            )
        ).first() is not None

    @staticmethod
    async def generate_late_payment_alerts(db: AsyncSession) -> int:
        """Crée des notifications de loyer en retard, ciblées sur les comptes concernés."""
        from app.models.lease import Lease
        from app.models.payment import Payment, PaymentStatus

        result = await db.execute(
            select(Payment, Lease)
            .join(Lease, Payment.lease_id == Lease.id)
            .where(Payment.status == PaymentStatus.LATE)
        )
        rows = result.all()

        created = 0
        for payment, lease in rows:
            recipients = await NotificationService._recipients_for_lease(db, lease)
            for uid in recipients:
                if await NotificationService._alert_exists(
                    db, NotificationType.LOYER_RETARD, "payment", payment.id, uid
                ):
                    continue
                db.add(
                    Notification(
                        notification_type=NotificationType.LOYER_RETARD,
                        priority=NotificationPriority.HIGH,
                        title="Loyer en retard",
                        message=(
                            f"Le loyer de {payment.period_label} "
                            f"(échéance {payment.due_date.strftime('%d/%m/%Y')}) "
                            f"n'a pas été reçu. Solde dû : {payment.balance:.2f} €."
                        ),
                        entity_type="payment",
                        entity_id=payment.id,
                        user_id=uid,
                    )
                )
                created += 1

        if created:
            await db.flush()
        return created

    @staticmethod
    async def generate_expiring_lease_alerts(db: AsyncSession) -> int:
        """Crée des notifications pour les baux expirant dans ≤ 90 jours."""
        from app.models.lease import Lease

        today = date.today()
        from datetime import timedelta

        horizon = today + timedelta(days=90)

        result = await db.execute(
            select(Lease).where(
                Lease.is_active == True,
                Lease.end_date != None,
                Lease.end_date <= horizon,
                Lease.end_date >= today,
            )
        )
        leases = result.scalars().all()

        created = 0
        for lease in leases:
            recipients = await NotificationService._recipients_for_lease(db, lease)
            if not recipients:
                continue
            days_left = (lease.end_date - today).days
            for uid in recipients:
                if await NotificationService._alert_exists(
                    db, NotificationType.BAIL_EXPIRE_SOON, "lease", lease.id, uid
                ):
                    continue
                db.add(
                    Notification(
                        notification_type=NotificationType.BAIL_EXPIRE_SOON,
                        priority=NotificationPriority.NORMAL
                        if days_left > 30
                        else NotificationPriority.HIGH,
                        title=f"Bail expirant dans {days_left} jour{'s' if days_left > 1 else ''}",
                        message=(
                            f"Le bail arrivera à échéance le "
                            f"{lease.end_date.strftime('%d/%m/%Y')} "
                            f"({days_left} jour{'s' if days_left > 1 else ''} restant{'s' if days_left > 1 else ''})."
                        ),
                        entity_type="lease",
                        entity_id=lease.id,
                        user_id=uid,
                    )
                )
                created += 1

        if created:
            await db.flush()
        return created
