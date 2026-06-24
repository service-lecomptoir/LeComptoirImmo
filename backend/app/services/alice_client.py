"""Client HTTP vers Alice (service-to-service, en-tête X-Internal-Key).

Alice est la source de vérité pour les plans, licences, entitlements et leads
(elle a sa propre base). LeComptoir Immo l'interroge via son API /internal —
plus aucune lecture directe des tables alice_* (elles n'existent plus ici).

Toutes les fonctions sont « fail-soft » : en cas d'indisponibilité d'Alice,
elles renvoient une valeur neutre (None / [] / False) et journalisent : l'app
ne casse jamais à cause d'Alice.
"""

import logging
import time
from uuid import UUID

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Cache mémoire de la licence par utilisateur : get_license est appelé sur le
# chemin d'authentification (chaque requête). Sans cache, c'est un appel HTTP à
# Alice par requête (+ ~timeout si Alice est lente/indisponible → latence sur
# TOUTES les requêtes). On mémorise le résultat (succès ET échec) un court instant.
_LICENSE_CACHE: dict = {}
_LICENSE_TTL = 60.0  # succès : revérifier au plus une fois / minute / user
_LICENSE_FAIL_TTL = 20.0  # échec/indispo : court (circuit-breaker, évite de réessayer en boucle)


def _base_headers():
    cfg = get_settings()
    return cfg.ALICE_URL, {"X-Internal-Key": cfg.ALICE_INTERNAL_KEY}


async def get_license(user_id: UUID, *, use_cache: bool = True) -> dict | None:
    """Licence/entitlements d'un gestionnaire : {is_blocked, plan_name, property_limit,
    access_until, features}. None si pas de licence (404) ou Alice indisponible.
    Résultat mis en cache (TTL court) pour ne pas appeler Alice à chaque requête."""
    key = str(user_id)
    now = time.monotonic()
    if use_cache:
        hit = _LICENSE_CACHE.get(key)
        if hit and hit[0] > now:
            return hit[1]

    base, headers = _base_headers()
    result: dict | None = None
    ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as hc:
            resp = await hc.get(f"{base}/api/v1/internal/license/{user_id}", headers=headers)
        if resp.status_code == 200:
            result, ok = resp.json(), True
        elif resp.status_code == 404:
            result, ok = None, True
        else:
            logger.warning("Alice get_license %s → %s", user_id, resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alice get_license failed for %s: %s", user_id, exc)

    _LICENSE_CACHE[key] = (now + (_LICENSE_TTL if ok else _LICENSE_FAIL_TTL), result)
    return result


def invalidate_license_cache(user_id: UUID | None = None) -> None:
    """Vide le cache licence (pour un user, ou tout). À appeler si la licence change."""
    if user_id is None:
        _LICENSE_CACHE.clear()
    else:
        _LICENSE_CACHE.pop(str(user_id), None)


async def list_plans() -> list[dict]:
    """Plans actifs (pour la page Tarification publique). [] si indisponible."""
    base, headers = _base_headers()
    try:
        async with httpx.AsyncClient(timeout=6.0) as hc:
            resp = await hc.get(
                f"{base}/api/v1/internal/plans", headers=headers, params={"product": "immo"}
            )
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Alice list_plans → %s", resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alice list_plans failed: %s", exc)
    return []


async def provision_residence_boutique(
    *,
    manager_email: str,
    immo_manager_id: UUID,
    residence_id: UUID,
    residence_kind: str,
    residence_name: str | None,
    residence_address: str | None = None,
) -> dict:
    """Demande à Alice de créer/lier la boutique Market d'une résidence.

    Renvoie {ok, status, data?, detail?}. `status == 409` + `detail == 'market_not_enabled'`
    signifie que le gestionnaire n'a pas (encore) de gérant Market : l'appelant
    affiche alors la CTA d'activation. N'est PAS fail-soft silencieux : on remonte
    le statut pour que le gestionnaire ait un retour clair."""
    base, headers = _base_headers()
    payload = {
        "manager_email": manager_email,
        "immo_manager_id": str(immo_manager_id),
        "residence_id": str(residence_id),
        "residence_kind": residence_kind,
        "residence_name": residence_name,
        "residence_address": residence_address,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as hc:
            resp = await hc.post(
                f"{base}/api/v1/internal/residence-boutique", headers=headers, json=payload
            )
        if resp.status_code in (200, 201):
            return {"ok": True, "status": resp.status_code, "data": resp.json()}
        detail = None
        try:
            detail = resp.json().get("detail")
        except Exception:  # noqa: BLE001
            detail = None
        logger.warning("Alice provision_residence_boutique → %s (%s)", resp.status_code, detail)
        return {"ok": False, "status": resp.status_code, "detail": detail}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alice provision_residence_boutique failed: %s", exc)
        return {"ok": False, "status": 502, "detail": "Alice injoignable"}


async def create_lead(
    full_name: str,
    email: str,
    phone: str | None = None,
    company: str | None = None,
    message: str | None = None,
    source: str = "site_lecomptoir",
) -> bool:
    """Crée une demande (souscription/démo/résiliation) côté Alice. True si OK."""
    base, headers = _base_headers()
    payload = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "company": company,
        "message": message,
        "source": source,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as hc:
            resp = await hc.post(f"{base}/api/v1/internal/leads", headers=headers, json=payload)
        if resp.status_code in (200, 201):
            return True
        logger.warning("Alice create_lead → %s", resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alice create_lead failed: %s", exc)
    return False
