"""
Scheduler APScheduler — tâches planifiées automatiques.
"""
import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Europe/Paris")
    return _scheduler


async def _job_update_late_payments() -> None:
    """Chaque jour à 8h : passe les paiements en retard."""
    from app.database import AsyncSessionLocal
    from app.services.payment_service import PaymentService

    async with AsyncSessionLocal() as db:
        try:
            count = await PaymentService.update_late_statuses(db)
            await db.commit()
            if count:
                logger.info(f"[Scheduler] {count} paiement(s) passé(s) en retard")
        except Exception as exc:
            logger.error(f"[Scheduler] update_late_payments error: {exc}")


async def _job_generate_alerts() -> None:
    """Chaque jour à 9h : génère alertes loyers retard + baux expirant."""
    from app.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            late = await NotificationService.generate_late_payment_alerts(db)
            expiring = await NotificationService.generate_expiring_lease_alerts(db)
            await db.commit()
            if late or expiring:
                logger.info(
                    f"[Scheduler] Alertes générées — retard:{late} expiration:{expiring}"
                )
        except Exception as exc:
            logger.error(f"[Scheduler] generate_alerts error: {exc}")


async def _job_generate_monthly_payments() -> None:
    """1er de chaque mois à 7h : génère les loyers du mois."""
    from app.database import AsyncSessionLocal
    from app.services.payment_service import PaymentService

    today = date.today()
    async with AsyncSessionLocal() as db:
        try:
            count = await PaymentService.generate_monthly(db, today.year, today.month)
            await db.commit()
            logger.info(
                f"[Scheduler] {count} loyer(s) généré(s) pour {today.month}/{today.year}"
            )
        except Exception as exc:
            logger.error(f"[Scheduler] generate_monthly_payments error: {exc}")


async def _job_generate_monthly_avis() -> None:
    """1er de chaque mois à 7h30 : génère les avis d'échéances et les envoie par email."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.database import AsyncSessionLocal
    from app.services.avis_echeance_service import AvisEcheanceService
    from app.services.email_service import send_avis_echeance
    from app.models.avis_echeance import AvisEcheance
    from app.models.tenant import Tenant

    today = date.today()
    months = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

    async with AsyncSessionLocal() as db:
        try:
            count = await AvisEcheanceService.generate_monthly_all(
                db, today.year, today.month
            )
            await db.commit()
            logger.info(
                f"[Scheduler] {count} avis d'échéance(s) généré(s) pour "
                f"{today.month}/{today.year}"
            )
        except Exception as exc:
            logger.error(f"[Scheduler] generate_monthly_avis error: {exc}")
            return

    # Envoi des emails — session séparée après commit
    async with AsyncSessionLocal() as db:
        try:
            avis_list = (await db.execute(
                select(AvisEcheance)
                .options(selectinload(AvisEcheance.tenant))
                .where(
                    AvisEcheance.period_year == today.year,
                    AvisEcheance.period_month == today.month,
                    AvisEcheance.generated_by.is_(None),  # auto-généré
                )
            )).scalars().all()

            period_label = f"{months[today.month]} {today.year}"
            sent = 0
            for avis in avis_list:
                tenant = avis.tenant
                if not tenant or not tenant.email:
                    continue
                ok = await send_avis_echeance(
                    to=tenant.email,
                    tenant_name=tenant.full_name or tenant.email,
                    period_label=period_label,
                    amount_total=float(avis.amount_total),
                    due_date=avis.due_date.strftime("%d/%m/%Y"),
                )
                if ok:
                    sent += 1

            if sent:
                logger.info(f"[Scheduler] {sent} email(s) avis d'échéance envoyé(s)")
        except Exception as exc:
            logger.error(f"[Scheduler] email_monthly_avis error: {exc}")


def start_scheduler(avis_day: int = 1, avis_hour: int = 7, avis_minute: int = 30) -> None:
    scheduler = get_scheduler()

    scheduler.add_job(
        _job_update_late_payments,
        CronTrigger(hour=8, minute=0),
        id="update_late_payments",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_generate_alerts,
        CronTrigger(hour=9, minute=0),
        id="generate_alerts",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_generate_monthly_payments,
        CronTrigger(day=1, hour=7, minute=0),
        id="generate_monthly_payments",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_generate_monthly_avis,
        CronTrigger(day=avis_day, hour=avis_hour, minute=avis_minute),
        id="generate_monthly_avis",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info(
        "[Scheduler] Démarré — 4 tâches planifiées (avis: jour=%d %02d:%02d)",
        avis_day, avis_hour, avis_minute,
    )


def reschedule_avis_job(day: int, hour: int, minute: int) -> None:
    """Reschedule dynamiquement le job avis d'échéance (appelé depuis l'API settings)."""
    scheduler = get_scheduler()
    if not scheduler.running:
        return
    scheduler.reschedule_job(
        "generate_monthly_avis",
        trigger=CronTrigger(day=day, hour=hour, minute=minute, timezone="Europe/Paris"),
    )
    logger.info("[Scheduler] Job avis reschedulé → jour=%d %02d:%02d", day, hour, minute)


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Arrêté")
