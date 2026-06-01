"""Catalogue canonique des fonctionnalités de plan (côté Alice).

Source de vérité backend, miroir de alice/frontend/src/constants/features.ts.
Ordre = ordre d'affichage. Toute NOUVELLE clé ajoutée ici est propagée
automatiquement (cochée) aux plans existants au démarrage (cf. main.py
`_propagate_new_features`) grâce au registre `alice_feature_registry`.
"""

FEATURE_KEYS = [
    "dashboard",
    "properties",
    "tenants",
    "leases",
    "avis_echeances",
    "payments",
    "quittances",
    "actualisation",
    "automatisation",
    "templates",
    "incidents",
    "entretiens",
    "contacts",
    "offres",
    "documents_caf",
    "admin",
    "finances",
    "performance_biens",
    "liasse_fiscale",
]

# Clés présentes AVANT la mise en place du mécanisme d'auto-ajout. Sert à
# amorcer le registre au 1er démarrage : `documents_caf` est ainsi détectée
# comme nouvelle et ajoutée aux plans existants (les autres restent inchangées,
# y compris celles que l'admin a décochées).
BASELINE_KEYS = [k for k in FEATURE_KEYS if k != "documents_caf"]
