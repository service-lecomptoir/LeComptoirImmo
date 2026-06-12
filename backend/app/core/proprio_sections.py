"""Rubriques de l'espace propriétaire que le gestionnaire peut activer ou non,
chacune liée (ou non) à une fonctionnalité du plan. Sert au calcul de ce qu'un
propriétaire voit en lecture seule (défaut d'agence + surcharge par compte) ∩ plan.
"""
from typing import Optional, List

# (clé, fonctionnalité de plan requise — None = toujours disponible)
PROPRIO_SECTIONS = [
    ("dashboard", None),
    ("biens", "properties"),
    ("revenus", "payments"),
    ("locataires", "tenants"),
    ("incidents", "incidents"),
    ("entretiens", "entretiens"),
    ("messages", None),
    ("fiscal", None),
    ("annonces", "diffusion"),
    ("candidatures", "candidatures"),
]
ALL_KEYS: List[str] = [k for k, _ in PROPRIO_SECTIONS]
_FEATURE_BY_KEY = dict(PROPRIO_SECTIONS)

LABELS = {
    "dashboard": "Tableau de bord",
    "biens": "Mes biens",
    "revenus": "Mes revenus",
    "locataires": "Mes locataires",
    "incidents": "Démarches",
    "entretiens": "Entretiens",
    "messages": "Messages",
    "fiscal": "Liasse fiscale",
    "annonces": "Annonces de mes biens",
    "candidatures": "Candidatures",
}


def plan_allowed_keys(plan_features: Optional[List[str]]) -> List[str]:
    """Rubriques autorisées par le plan (None = toutes)."""
    if plan_features is None:
        return list(ALL_KEYS)
    feats = set(plan_features)
    return [k for k, f in PROPRIO_SECTIONS if f is None or f in feats]


def sanitize(keys) -> List[str]:
    """Ne garde que des clés valides, dans l'ordre canonique."""
    s = set(keys or [])
    return [k for k in ALL_KEYS if k in s]


def effective_keys(override, agency_default, plan_features) -> List[str]:
    """Visibilité effective : surcharge si définie, sinon défaut d'agence, sinon
    toutes les rubriques ; le tout intersecté avec le plan."""
    if override is not None:
        base = override
    elif agency_default is not None:
        base = agency_default
    else:
        base = list(ALL_KEYS)
    allowed = set(plan_allowed_keys(plan_features))
    return [k for k in sanitize(base) if k in allowed]
