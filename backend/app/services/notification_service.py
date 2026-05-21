import uuid
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType, NotificationPriority
from app.schemas.notification import NotificationCreate
from app.core.exceptions import NotFoundException


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
                or_(Notification.user_id == user_id, Notification.user_id == None),
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
        """Returns (items, total, unread_count)."""
        query = select(Notification).where(
            or_(Notification.user_id == user_id, Notification.user_id == None)
        )
        if unread_only:
            query = query.where(Notification.is_read == False)

        total_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_q)).scalar_one()

        unread_q = select(func.count(Notification.id)).where(
            Notification.is_read == False,
            or_(Notification.user_id == user_id, Notification.user_id == None),
        )
        unread_count = (await db.execute(unread_q)).scalar_one()

        items = (
            await db.execute(
                query.order_by(Notification.created_at.desc()).limit(limit)
            )
        ).scalars().all()

        return list(items), total, unread_count

    @staticmethod
    async def mark_read(db: AsyncSession, notification_id: uuid.UUID) -> Notification:
        notif = await db.get(Notification, notification_id)
        if not notif:
            raise NotFoundException("Notification introuvable")
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(Notification).where(
                Notification.is_read == False,
                or_(Notification.user_id == user_id, Notification.user_id == None),
            )
        )
        notifs = result.scalars().all()
        now = datetime.now(timezone.utc)
        for n in notifs:
            n.is_read = True
            n.read_at = now
        await db.flush()
        return len(notifs)

    # ── Génération d'alertes automatiques ─────────────────────────────────────

    @staticmethod
    async def generate_late_payment_alerts(db: AsyncSession) -> int:
        """Crée des notifications pour les loyers en retard non encore notifiés."""
        from app.models.payment import Payment, PaymentStatus

        result = await db.execute(
            select(Payment).where(Payment.status == PaymentStatus.LATE)
        )
        late_payments = result.scalars().all()

        created = 0
        for payment in late_payments:
            # Vérifier qu'une notification n'existe pas déjà pour ce paiement
            existing = (
                await db.execute(
                    select(Notification).where(
                        Notification.notification_type == NotificationType.LOYER_RETARD,
                        Notification.entity_type == "payment",
                        Notification.entity_id == payment.id,
                    )
                )
            ).scalar_one_or_none()

            if not existing:
                notif = Notification(
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
                    user_id=None,  # broadcast
                )
                db.add(notif)
                created += 1

        if created:
            await db.flush()
        return created

    @staticmethod
    async def generate_expiring_lease_alerts(db: AsyncSession) -> int:
        """Crée des notifications pour les baux expirant dans ≤ 90 jours."""
        from app.models.lease import Lease
        from sqlalchemy import and_

        today = date.today()
        in_90_days = date(today.year, today.month, today.day)
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
            existing = (
                await db.execute(
                    select(Notification).where(
                        Notification.notification_type == NotificationType.BAIL_EXPIRE_SOON,
                        Notification.entity_type == "lease",
                        Notification.entity_id == lease.id,
                    )
                )
            ).scalar_one_or_none()

            if not existing:
                days_left = (lease.end_date - today).days
                notif = Notification(
                    notification_type=NotificationType.BAIL_EXPIRE_SOON,
                    priority=NotificationPriority.NORMAL if days_left > 30 else NotificationPriority.HIGH,
                    title=f"Bail expirant dans {days_left} jour(s)",
                    message=(
                        f"Le bail arrivera à échéance le "
                        f"{lease.end_date.strftime('%d/%m/%Y')} "
                        f"({days_left} jours restants)."
                    ),
                    entity_type="lease",
                    entity_id=lease.id,
                    user_id=None,
                )
                db.add(notif)
                created += 1

        if created:
            await db.flush()
        return created
