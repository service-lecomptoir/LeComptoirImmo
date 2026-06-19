"""
Scheduler APScheduler : tâches planifiées automatiques.
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
                    f"[Scheduler] Alertes générées : retard:{late} expiration:{expiring}"
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
    """1er de chaque mois : GÉNÈRE les avis d'échéances (données). L'ENVOI est
    entièrement piloté par les règles d'automatisation (voir _job_run_automation_rules)
    — aucun envoi en dur ici."""
    from app.database import AsyncSessionLocal
    from app.services.avis_echeance_service import AvisEcheanceService

    today = date.today()
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


async def _job_run_automation_rules() -> None:
    """Toutes les 5 min : exécute les automatisations dont l'heure d'exécution
    (hh:mm, réglée dans l'onglet Auto Génération) est atteinte ce jour, une fois
    par jour. Heure de référence = Europe/Paris. SEUL émetteur automatique."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.database import AsyncSessionLocal
    from app.services import automation_engine

    now = datetime.now(ZoneInfo("Europe/Paris"))
    async with AsyncSessionLocal() as db:
        try:
            summary = await automation_engine.run_all(db, now.date(), now=now)
            await db.commit()
            if summary:
                logger.info(f"[Scheduler] Auto Génération {now:%H:%M} : {summary}")
        except Exception as exc:
            logger.error(f"[Scheduler] run_automation_rules error: {exc}")


async def _job_send_telegram_reminders() -> None:
    """Rappel quotidien « point du jour » envoyé sur Telegram aux gestionnaires liés.

    N'envoie qu'aux comptes liés + opt-in, dont le plan inclut l'option « agents_ia ».
    Chaque synthèse est scopée au périmètre du gestionnaire (isolation par rôle).
    No-op si le canal Telegram n'est pas configuré ou si le rappel est désactivé."""
    from sqlalchemy import select
    from app.config import get_settings
    from app.database import AsyncSessionLocal
    from app.services import settings_service, agent_team_service
    from app.services.telegram_service import send_message
    from app.core.features import get_plan_features
    from app.models.telegram_link import TelegramLink
    from app.models.user import User

    if not get_settings().telegram_enabled:
        return

    async with AsyncSessionLocal() as db:
        try:
            cfg = await settings_service.get_reminder_config(db)
            if not cfg["enabled"]:
                return
            links = (await db.execute(
                select(TelegramLink).where(
                    TelegramLink.opt_in.is_(True),
                    TelegramLink.chat_id.isnot(None),
                )
            )).scalars().all()

            sent = 0
            for link in links:
                user = await db.get(User, link.user_id)
                if not user or not user.is_active:
                    continue
                feats = await get_plan_features(db, user.id)
                if feats is not None and "agents_ia" not in feats:
                    continue  # option non incluse dans le plan
                try:
                    text = await agent_team_service.reminders(db, user)
                    if await send_message(link.chat_id, text):
                        sent += 1
                except Exception as exc:  # noqa: BLE001 : un compte ne bloque pas les autres
                    logger.warning("[Scheduler] rappel Telegram échec user=%s: %r", user.id, exc)
            if sent:
                logger.info("[Scheduler] %d rappel(s) Telegram envoyé(s)", sent)
        except Exception as exc:
            logger.error(f"[Scheduler] telegram_reminders error: {exc}")


async def _job_publish_scheduled_listings() -> None:
    """Toutes les 10 min : publie les annonces programmées arrivées à échéance."""
    from app.database import AsyncSessionLocal
    from app.services.listing_service import ListingService

    async with AsyncSessionLocal() as db:
        try:
            count = await ListingService.publish_due(db)
            await db.commit()
            if count:
                logger.info(f"[Scheduler] {count} annonce(s) programmée(s) publiée(s)")
        except Exception as exc:
            logger.error(f"[Scheduler] publish_scheduled_listings error: {exc}")


async def _job_signalement_noise_reminders() -> None:
    """Chaque lundi à 10h : rappels préventifs de bon voisinage aux biens ayant un
    historique de signalements de bruit (throttlé, voir SignalementAlertService)."""
    from app.database import AsyncSessionLocal
    from app.services.signalement_alert_service import SignalementAlertService

    async with AsyncSessionLocal() as db:
        try:
            n = await SignalementAlertService.run_preventive_reminders(db)
            await db.commit()
            if n:
                logger.info(f"[Scheduler] {n} rappel(s) préventif(s) bruit envoyé(s)")
        except Exception as exc:
            logger.error(f"[Scheduler] signalement_noise_reminders error: {exc}")


async def _job_visit_reminders() -> None:
    """Chaque jour à 9h30 : relance les candidats dont la visite réservée a lieu
    dans les 48h (une seule fois, voir Candidature.visit_reminded_at)."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.candidature import Candidature
    from app.models.visit import PropertyVisitSlot
    from app.api.v1.candidatures import send_candidature_visit_reminder

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            horizon = now + timedelta(hours=48)
            rows = (await db.execute(
                select(Candidature)
                .join(PropertyVisitSlot, Candidature.visit_slot_id == PropertyVisitSlot.id)
                .where(
                    Candidature.visit_reminded_at.is_(None),
                    Candidature.status != "refusee",
                    PropertyVisitSlot.starts_at > now,
                    PropertyVisitSlot.starts_at <= horizon,
                )
            )).scalars().all()
            n = 0
            for c in rows:
                try:
                    if await send_candidature_visit_reminder(db, c, respect_active=True):
                        n += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"[Scheduler] visit reminder {c.id} error: {exc}")
            await db.commit()
            if n:
                logger.info(f"[Scheduler] {n} relance(s) avant visite envoyée(s)")
        except Exception as exc:
            logger.error(f"[Scheduler] visit_reminders error: {exc}")


async def _job_candidature_doc_reminders() -> None:
    """Chaque jour à 10h : relance UNE fois les candidats dont le dossier reste
    incomplet (pièces demandées non déposées) plus de 3 jours après la demande.
    Respecte l'interrupteur de la règle « candidature : demande de pièces »."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.candidature import Candidature
    from app.api.v1.candidatures import send_candidature_docs_reminder

    async with AsyncSessionLocal() as db:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=3)
            rows = (await db.execute(
                select(Candidature).where(
                    Candidature.status == "documents_demandes",
                    Candidature.docs_reminded_at.is_(None),
                    Candidature.upload_token.isnot(None),
                    Candidature.created_at < cutoff,
                )
            )).scalars().all()
            n = 0
            for c in rows:
                try:
                    if await send_candidature_docs_reminder(db, c, respect_active=True):
                        n += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"[Scheduler] doc reminder {c.id} error: {exc}")
            await db.commit()
            if n:
                logger.info(f"[Scheduler] {n} relance(s) dossier incomplet envoyée(s)")
        except Exception as exc:
            logger.error(f"[Scheduler] candidature_doc_reminders error: {exc}")


async def _job_vacancy_alerts() -> None:
    """Chaque jour à 10h : alerte UNE fois le gestionnaire (agent Administratif +
    notification) pour chaque annonce publiée depuis plus de 7 jours qui n'a reçu
    AUCUNE candidature. Aide commerciale : relancer la diffusion / revoir le prix."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, func
    from app.database import AsyncSessionLocal
    from app.models.publishing import Listing
    from app.models.candidature import Candidature
    from app.models.property import Property
    from app.models.notification import Notification, NotificationType, NotificationPriority
    from app.services import agent_events

    async with AsyncSessionLocal() as db:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            rows = (await db.execute(
                select(Listing).where(
                    Listing.status == "published",
                    Listing.vacancy_alerted_at.is_(None),
                    Listing.published_at.isnot(None),
                    Listing.published_at < cutoff,
                )
            )).scalars().all()
            n = 0
            for lst in rows:
                cnt = (await db.execute(
                    select(func.count(Candidature.id)).where(Candidature.property_id == lst.property_id)
                )).scalar() or 0
                if cnt:
                    continue
                prop = await db.get(Property, lst.property_id)
                pname = prop.name if prop else "votre bien"
                days = (datetime.now(timezone.utc) - lst.published_at).days
                if lst.created_by:
                    db.add(Notification(
                        title="Annonce sans candidature",
                        message=(f"L'annonce « {pname} » est publiée depuis {days} jours sans aucune "
                                 f"candidature. Pensez à élargir la diffusion ou à revoir le loyer."),
                        notification_type=NotificationType.SYSTEME, priority=NotificationPriority.NORMAL,
                        entity_type="listing", entity_id=lst.id, user_id=lst.created_by,
                    ))
                await agent_events.notify_manager(
                    db, lst.created_by, "vacance",
                    f"L'annonce <b>{pname}</b> est publiée depuis {days} jours sans aucune candidature.",
                    cta="Élargissez la diffusion ou revoyez le loyer dans « Publication des annonces ».",
                )
                lst.vacancy_alerted_at = datetime.now(timezone.utc)
                n += 1
            await db.commit()
            if n:
                logger.info(f"[Scheduler] {n} alerte(s) vacance envoyée(s)")
        except Exception as exc:
            logger.error(f"[Scheduler] vacancy_alerts error: {exc}")


def start_scheduler(
    avis_day: int = 1, avis_hour: int = 7, avis_minute: int = 30,
    reminder_hour: int = 8, reminder_minute: int = 0,
) -> None:
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
    scheduler.add_job(
        _job_run_automation_rules,
        CronTrigger(minute="*/5"),  # toutes les 5 min ; chaque règle tourne 1×/jour à son hh:mm
        id="run_automation_rules",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_send_telegram_reminders,
        CronTrigger(hour=reminder_hour, minute=reminder_minute),
        id="telegram_reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_publish_scheduled_listings,
        CronTrigger(minute="*/10"),
        id="publish_scheduled_listings",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_signalement_noise_reminders,
        CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="signalement_noise_reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_visit_reminders,
        CronTrigger(hour=9, minute=30),
        id="visit_reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_candidature_doc_reminders,
        CronTrigger(hour=10, minute=0),
        id="candidature_doc_reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _job_vacancy_alerts,
        CronTrigger(hour=10, minute=15),
        id="vacancy_alerts",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info(
        "[Scheduler] Démarré : 8 tâches planifiées (avis: jour=%d %02d:%02d ; "
        "rappels Telegram: %02d:%02d ; publication annonces: */10 min ; "
        "rappels bruit: lundi 10:00)",
        avis_day, avis_hour, avis_minute, reminder_hour, reminder_minute,
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


def reschedule_reminder_job(hour: int, minute: int) -> None:
    """Reschedule dynamiquement le job de rappels Telegram (API settings)."""
    scheduler = get_scheduler()
    if not scheduler.running:
        return
    scheduler.reschedule_job(
        "telegram_reminders",
        trigger=CronTrigger(hour=hour, minute=minute, timezone="Europe/Paris"),
    )
    logger.info("[Scheduler] Job rappels Telegram reschedulé → %02d:%02d", hour, minute)


async def run_telegram_reminders_now() -> None:
    """Déclenche immédiatement l'envoi des rappels (test manuel via API)."""
    await _job_send_telegram_reminders()


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Arrêté")
