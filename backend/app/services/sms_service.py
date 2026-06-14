"""Service d'envoi de SMS transactionnels via Brevo (ex-Sendinblue).

API : POST https://api.brevo.com/v3/transactionalSMS/sms (en-tête `api-key`).
Fail-soft : si BREVO_API_KEY est vide (SMS désactivé) ou en cas d'erreur, on
journalise et on renvoie False — l'app ne casse jamais à cause du SMS.
"""
import logging
import re
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_BREVO_SMS_URL = "https://api.brevo.com/v3/transactionalSMS/sms"


def normalize_phone(raw: Optional[str], default_country: str = "FR") -> Optional[str]:
    """Met un numéro au format international E.164 (ex. « 06 12 34 56 78 » → « +33612345678 »).
    Retourne None si le numéro est inexploitable. Couvre la France + DOM (préfixe +33)."""
    if not raw:
        return None
    s = re.sub(r"[^\d+]", "", str(raw))
    if not s:
        return None
    if s.startswith("+"):
        return s
    if s.startswith("00"):
        return "+" + s[2:]
    # Numéro national français : 0X XX XX XX XX → +33XXXXXXXXX
    if default_country == "FR" and s.startswith("0") and len(s) == 10:
        return "+33" + s[1:]
    # Déjà sans 0 et longueur plausible → préfixe pays par défaut
    if default_country == "FR" and len(s) == 9:
        return "+33" + s
    return None


async def send_sms(to: str, content: str) -> bool:
    """Envoie un SMS transactionnel. Retourne True si envoyé, False si désactivé/erreur."""
    cfg = get_settings()
    recipient = normalize_phone(to)
    if not recipient:
        logger.warning("SMS non envoyé : numéro invalide %r", to)
        return False

    if not cfg.sms_enabled:
        logger.debug("SMS désactivé : SMS simulé vers %s: %s", recipient, content[:60])
        return False

    payload = {
        "sender": cfg.SMS_SENDER,
        "recipient": recipient,
        "content": content,
        "type": "transactional",
    }
    headers = {"api-key": cfg.BREVO_API_KEY, "accept": "application/json",
               "content-type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as hc:
            resp = await hc.post(_BREVO_SMS_URL, json=payload, headers=headers)
        if resp.status_code in (200, 201):
            return True
        logger.warning("Brevo send_sms %s → %s : %s", recipient, resp.status_code, resp.text[:200])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Brevo send_sms failed for %s: %s", recipient, exc)
    return False
