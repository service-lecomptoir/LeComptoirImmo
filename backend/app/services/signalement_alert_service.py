"""Moteur d'alertes « bruit » des signalements (étape 2).

Déclenché à la création d'un signalement (bruit) ET par un job planifié :
  • Nocturne : bruit signalé entre 22h et 7h → message courtois à l'appartement
    concerné + le gestionnaire est informé. Historisé.
  • Escalade : si un bien cumule des signalements de bruit (≥ seuil sur la fenêtre),
    on alerte le gestionnaire (une fois par fenêtre, pas de spam).
  • Préventif : job périodique qui relance un rappel courtois aux biens à historique
    de bruit (throttlé).

Canal actuel = notification in-app (SMTP/SMS pas encore actifs) ; le code est prêt à
brancher un autre canal plus tard. Toutes les alertes sont journalisées dans
`signalement_alerts`.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signalement import Signalement
from app.models.signalement_alert import SignalementAlert, AlertType
from app.models.lease import Lease
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.notification import Notification, NotificationType, NotificationPriority

# Réglages (valeurs par défaut raisonnables ; ajustables ultérieurement).
NIGHT_START_HOUR = 22          # 22h
NIGHT_END_HOUR = 7             # 7h
ESCALATION_WINDOW_DAYS = 30
ESCALATION_THRESHOLD = 3       # nb de bruits sur la fenêtre déclenchant l'escalade
PREVENTIVE_WINDOW_DAYS = 60
PREVENTIVE_MIN_NOISE = 2       # historique mini pour relancer un rappel préventif
PREVENTIVE_THROTTLE_DAYS = 14  # pas plus d'un rappel préventif / bien / 14 j

_COURTESY_MSG = (
    "Une nuisance sonore a été signalée durant la nuit. Merci à chacun de veiller à la "
    "tranquillité de tous et de limiter le bruit après 22h."
)
_PREVENTIVE_MSG = (
    "Rappel de bon voisinage : merci de veiller à réduire le bruit après 22h pour le "
    "confort de tous les occupants."
)


def is_night(dt: Optional[datetime]) -> bool:
    """Vrai si l'heure est dans la plage nocturne [22h, 7h[."""
    if dt is None:
        return False
    return dt.hour >= NIGHT_START_HOUR or dt.hour < NIGHT_END_HOUR


class SignalementAlertService:

    @staticmethod
    async def _property_tenant_user_ids(db: AsyncSession, property_id) -> list[uuid.UUID]:
        """Comptes locataires (user_id) des baux actifs du bien — destinataires du message."""
        if not property_id:
            return []
        rows = await db.execute(
            select(Tenant.user_id)
            .join(Lease, Lease.tenant_id == Tenant.id)
            .where(Lease.property_id == property_id, Lease.is_active.is_(True),
                   Tenant.user_id.isnot(None))
        )
        return [uid for uid in rows.scalars().all() if uid]

    @staticmethod
    def _notify(db: AsyncSession, user_id, title: str, message: str,
                priority=NotificationPriority.NORMAL, signalement_id=None) -> None:
        if not user_id:
            return
        db.add(Notification(
            title=title, message=message[:200],
            notification_type=NotificationType.SYSTEME, priority=priority,
            entity_type="signalement", entity_id=signalement_id, user_id=user_id,
        ))

    @staticmethod
    def _log(db: AsyncSession, alert_type: str, property_id, signalement_id,
             recipient_user_id, message: str) -> None:
        db.add(SignalementAlert(
            alert_type=alert_type, property_id=property_id, signalement_id=signalement_id,
            recipient_user_id=recipient_user_id, message=message,
        ))

    @staticmethod
    async def process_new(db: AsyncSession, s: Signalement) -> None:
        """Hook appelé après création d'un signalement (même transaction).

        Ne traite que le bruit. Best-effort : toute erreur est avalée pour ne jamais
        bloquer la création du signalement."""
        try:
            if s.category != "bruit":
                return
            # 1) Alerte nocturne : message courtois à l'appartement concerné.
            if is_night(s.occurred_at):
                tenant_uids = await SignalementAlertService._property_tenant_user_ids(db, s.property_id)
                for uid in tenant_uids:
                    SignalementAlertService._notify(
                        db, uid, "Nuisance sonore signalée la nuit", _COURTESY_MSG,
                        NotificationPriority.NORMAL, s.id)
                    SignalementAlertService._log(db, AlertType.NOCTURNE.value, s.property_id, s.id, uid, _COURTESY_MSG)
                if not tenant_uids:
                    # Aucun compte locataire : on journalise quand même l'alerte nocturne.
                    SignalementAlertService._log(db, AlertType.NOCTURNE.value, s.property_id, s.id, None, _COURTESY_MSG)

            # 2) Escalade gestionnaire si récurrence de bruit sur le bien.
            await SignalementAlertService._maybe_escalate(db, s)
        except Exception:  # noqa: BLE001 : ne jamais bloquer la création
            pass

    @staticmethod
    async def _maybe_escalate(db: AsyncSession, s: Signalement) -> None:
        if not s.property_id:
            return
        since = datetime.utcnow() - timedelta(days=ESCALATION_WINDOW_DAYS)
        count = (await db.execute(
            select(func.count(Signalement.id)).where(
                Signalement.property_id == s.property_id,
                Signalement.category == "bruit",
                Signalement.created_at >= since,
            )
        )).scalar_one()
        if count < ESCALATION_THRESHOLD:
            return
        # Anti-spam : pas de nouvelle escalade si une existe déjà sur la fenêtre.
        recent = (await db.execute(
            select(func.count(SignalementAlert.id)).where(
                SignalementAlert.property_id == s.property_id,
                SignalementAlert.alert_type == AlertType.ESCALADE.value,
                SignalementAlert.created_at >= since,
            )
        )).scalar_one()
        if recent:
            return
        prop = await db.get(Property, s.property_id)
        manager_id = getattr(prop, "created_by", None) if prop else None
        name = (prop.name if prop else "Un bien")
        msg = (f"Le bien « {name} » fait l'objet de {count} signalements de bruit sur "
               f"{ESCALATION_WINDOW_DAYS} jours. Une action de votre part est recommandée.")
        SignalementAlertService._notify(db, manager_id, "Bruit récurrent : action recommandée",
                                        msg, NotificationPriority.HIGH, s.id)
        SignalementAlertService._log(db, AlertType.ESCALADE.value, s.property_id, s.id, manager_id, msg)

    @staticmethod
    async def run_preventive_reminders(db: AsyncSession) -> int:
        """Job périodique : relance un rappel préventif courtois aux biens à historique
        de bruit, sans spammer (throttle PREVENTIVE_THROTTLE_DAYS). Retourne le nb de
        biens relancés."""
        since = datetime.utcnow() - timedelta(days=PREVENTIVE_WINDOW_DAYS)
        rows = await db.execute(
            select(Signalement.property_id, func.count(Signalement.id))
            .where(Signalement.category == "bruit", Signalement.created_at >= since,
                   Signalement.property_id.isnot(None))
            .group_by(Signalement.property_id)
            .having(func.count(Signalement.id) >= PREVENTIVE_MIN_NOISE)
        )
        targets = [(pid, n) for pid, n in rows.all()]
        throttle_since = datetime.utcnow() - timedelta(days=PREVENTIVE_THROTTLE_DAYS)
        done = 0
        for pid, _n in targets:
            recent = (await db.execute(
                select(func.count(SignalementAlert.id)).where(
                    SignalementAlert.property_id == pid,
                    SignalementAlert.alert_type == AlertType.PREVENTIF.value,
                    SignalementAlert.created_at >= throttle_since,
                )
            )).scalar_one()
            if recent:
                continue
            uids = await SignalementAlertService._property_tenant_user_ids(db, pid)
            for uid in uids:
                SignalementAlertService._notify(db, uid, "Rappel de bon voisinage",
                                                _PREVENTIVE_MSG, NotificationPriority.LOW)
            SignalementAlertService._log(db, AlertType.PREVENTIF.value, pid, None,
                                         uids[0] if uids else None, _PREVENTIVE_MSG)
            done += 1
        return done
