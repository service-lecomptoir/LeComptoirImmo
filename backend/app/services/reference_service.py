# -*- coding: utf-8 -*-
"""Identifiants lisibles uniques (« ref_code ») attribués à la création.

Nomenclature : « PREFIXE-NNNNN » (séquence à 5 chiffres, propre à chaque préfixe).
  • Comptes (users), préfixe selon le rôle :
      gestionnaire -> GM, gestionnaire_proprio -> GP, admin -> AD,
      comptable -> CB, proprietaire -> UP, locataire -> UL, lecture -> LE
  • Fiche propriétaire (owners) -> PR
  • Bien / propriété (properties) -> BN
  • Fiche locataire (tenants) -> LO

Utilisé partout où un « numéro associé » est demandé (avatar, quittance, avis…).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

USER_PREFIX = {
    "gestionnaire": "GM",
    "gestionnaire_proprio": "GP",
    "admin": "AD",
    "comptable": "CB",
    "proprietaire": "UP",
    "locataire": "UL",
    "lecture": "LE",
}


def user_prefix(role) -> str:
    # `role` peut être un membre d'enum Role (str(member) == « Role.X ») ou une
    # chaîne : on prend la valeur (« proprietaire »…) pour matcher la table.
    key = getattr(role, "value", None) or str(role)
    return USER_PREFIX.get(str(key), "UT")


def _seq_of(ref) -> int:
    """Numéro de séquence d'un ref_code (« GM-00007 » -> 7), 0 si illisible."""
    try:
        return int(str(ref).rsplit("-", 1)[-1])
    except (ValueError, TypeError, AttributeError):
        return 0


async def make_ref(db: AsyncSession, column, prefix: str) -> str:
    """Prochain identifiant disponible pour ce préfixe (max existant + 1)."""
    rows = (await db.execute(
        select(column).where(column.like(f"{prefix}-%"))
    )).scalars().all()
    nxt = max((_seq_of(r) for r in rows), default=0) + 1
    return f"{prefix}-{nxt:05d}"


async def backfill_table(db: AsyncSession, model, prefix_for) -> int:
    """Attribue un ref_code aux lignes existantes qui n'en ont pas (reprise
    historique). `prefix_for(row)` donne le préfixe. Idempotent : ne touche que
    les ref_code vides. Numérotation stable par ordre de création."""
    rows = (await db.execute(
        select(model).order_by(model.created_at, model.id)
    )).scalars().all()
    counters: dict[str, int] = {}
    for r in rows:
        rc = getattr(r, "ref_code", None)
        if rc and "-" in str(rc):
            p = str(rc).rsplit("-", 1)[0]
            counters[p] = max(counters.get(p, 0), _seq_of(rc))
    changed = 0
    for r in rows:
        if getattr(r, "ref_code", None):
            continue
        p = prefix_for(r)
        counters[p] = counters.get(p, 0) + 1
        r.ref_code = f"{p}-{counters[p]:05d}"
        changed += 1
    if changed:
        await db.flush()
    return changed
