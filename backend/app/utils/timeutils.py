"""Utilitaires date/heure.

`utcnow()` remplace `datetime.utcnow()` (déprécié) par l'API non dépréciée, en
conservant EXACTEMENT la même valeur : un datetime UTC **naïf**. C'est volontaire :
la majorité des colonnes du schéma sont des `TIMESTAMP` sans fuseau (naïfs), et
asyncpg refuse d'écrire/comparer un datetime *aware* avec ces colonnes. Passer en
*aware* nécessiterait d'abord de migrer ces colonnes en `timestamptz`.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Horodatage UTC naïf (équivalent non déprécié de datetime.utcnow())."""
    return datetime.now(UTC).replace(tzinfo=None)
