"""Catalogue CANONIQUE des fonctionnalités (source de vérité unique).

Tout part d'ici : les clés d'entitlement (core/features.FEATURE_KEYS), la liste
des fonctionnalités d'un plan (LeComptoir Alice), la page Tarification publique et
le Guide utilisateur (généré dynamiquement). Exposé via GET /api/v1/public/features.

Ajouter / renommer / décrire une fonctionnalité => modifier UNIQUEMENT ce fichier ;
le menu (routing), le guide, les plans Alice et les tarifs se mettent à jour.
"""
from typing import List, Dict

# Catégories d'affichage (ordre = ordre des sections).
CATEGORY_MISE_EN_LOCATION = "Mise en location"
CATEGORY_GESTION = "Gestion locative"
CATEGORY_FINANCE = "Finance et comptabilité"
CATEGORY_IA = "Assistance"

# Chaque entrée : key (stable), label, description, category, order.
FEATURE_CATALOG: List[Dict] = [
    # ── Mise en location ───────────────────────────────────────────────────────
    {"key": "diffusion", "label": "Publication des annonces", "category": CATEGORY_MISE_EN_LOCATION,
     "description": "Création et personnalisation des annonces (photos, description, critères), diffusion sur vos plateformes, publication immédiate ou programmée et suivi des performances (vues)."},
    {"key": "candidatures", "label": "Gestion des candidatures", "category": CATEGORY_MISE_EN_LOCATION,
     "description": "Dossiers candidats centralisés : demande de pièces par lien sécurisé, proposition de visite avec réservation en ligne, comparaison des profils, acceptation et passage en locataire."},
    # ── Gestion locative ───────────────────────────────────────────────────────
    {"key": "dashboard", "label": "Tableau de bord", "category": CATEGORY_GESTION,
     "description": "Vue d'ensemble : indicateurs clés, revenus et alertes en un coup d'œil."},
    {"key": "properties", "label": "Propriétés", "category": CATEGORY_GESTION,
     "description": "Gérez tous vos biens : caractéristiques, adresse, équipements et occupation."},
    {"key": "tenants", "label": "Locataires", "category": CATEGORY_GESTION,
     "description": "Fiches locataires : coordonnées, pièces justificatives et historique."},
    {"key": "leases", "label": "Contrats", "category": CATEGORY_GESTION,
     "description": "Contrats de location : baux, co-titulaires, dates et conditions."},
    {"key": "avis_echeances", "label": "Avis d'échéances", "category": CATEGORY_GESTION,
     "description": "Génération automatique des avis d'échéance selon la fréquence du bail."},
    {"key": "payments", "label": "Paiements", "category": CATEGORY_GESTION,
     "description": "Suivi des paiements : encaissements, déclarations, relances et soldes."},
    {"key": "quittances", "label": "Quittances de loyer", "category": CATEGORY_GESTION,
     "description": "Quittances de loyer en PDF, à votre charte, prêtes à envoyer."},
    {"key": "actualisation", "label": "Révision des loyers et charges", "category": CATEGORY_GESTION,
     "description": "Révision du loyer (IRL ou réévaluation amiable), régularisation et réévaluation des provisions de charges, et décompte de taxes foncières (TEOM)."},
    {"key": "automatisation", "label": "Communication et automatisation", "category": CATEGORY_GESTION,
     "description": "Modèles de courrier multilingues, automatisation des envois (avis, quittances, relances) et apparence des e-mails."},
    {"key": "templates", "label": "Atelier de documents", "category": CATEGORY_GESTION,
     "description": "Vos modèles de documents personnalisés (logo, en-tête, mentions, blocs)."},
    {"key": "incidents", "label": "Démarche", "category": CATEGORY_GESTION,
     "description": "Démarches : demandes de vos locataires, échanges et suivi (relance, clôture), et signalements de la résidence."},
    {"key": "entretiens", "label": "Entretiens", "category": CATEGORY_GESTION,
     "description": "Planification et suivi des entretiens et interventions sur vos biens."},
    {"key": "contacts", "label": "Carnet d'adresses", "category": CATEGORY_GESTION,
     "description": "Carnet d'adresses : artisans, prestataires et contacts utiles."},
    {"key": "offres", "label": "Offres & Services", "category": CATEGORY_GESTION,
     "description": "Offres & services partenaires proposés à vos locataires."},
    {"key": "documents_caf", "label": "Espace CAF", "category": CATEGORY_GESTION,
     "description": "Espace CAF : attestation de loyer et formulaire tiers payant, + rappel de déclaration de loyer (juillet→décembre)."},
    {"key": "sortie_locataire", "label": "Sortie du locataire", "category": CATEGORY_GESTION,
     "description": "Suivi des préavis, état des lieux de sortie comparé à l'entrée, décompte du dépôt de garantie et clôture du dossier."},
    {"key": "admin", "label": "Gestion des utilisateurs", "category": CATEGORY_GESTION,
     "description": "Gestion des comptes utilisateurs et des accès de votre espace."},
    # ── Finance et comptabilité ────────────────────────────────────────────────
    {"key": "finances", "label": "Revenus et comptabilité", "category": CATEGORY_FINANCE,
     "description": "Suivi des revenus locatifs et grand livre comptable, par propriétaire et par période."},
    {"key": "performance_biens", "label": "Performance des biens", "category": CATEGORY_FINANCE,
     "description": "Performance par bien : loyer théorique vs perçu, taux d'occupation."},
    {"key": "liasse_fiscale", "label": "Liasse fiscale", "category": CATEGORY_FINANCE,
     "description": "Génération de la liasse fiscale (revenus fonciers) pour vos déclarations."},
    # ── Assistance ─────────────────────────────────────────────────────────────
    {"key": "agents_ia", "label": "Agents IA", "category": CATEGORY_IA,
     "description": "Équipe d'agents IA (Comptable, Sécurité, Administratif) accessible par Telegram : rappels, questions et instructions."},
]

# Clés canoniques (set) dérivées du catalogue.
FEATURE_KEYS = {f["key"] for f in FEATURE_CATALOG}


def public_catalog() -> List[Dict]:
    """Catalogue sérialisable (avec ordre) pour l'API publique."""
    return [
        {"key": f["key"], "label": f["label"], "description": f["description"],
         "category": f["category"], "order": i}
        for i, f in enumerate(FEATURE_CATALOG)
    ]
