"""Catalogue CANONIQUE des fonctionnalités (source de vérité unique).

Tout part d'ici : les clés d'entitlement (core/features.FEATURE_KEYS), la liste
des fonctionnalités d'un plan (LeComptoir Alice), la page Tarification publique et
le Guide utilisateur (généré dynamiquement). Exposé via GET /api/v1/public/features.

Ajouter / renommer / décrire une fonctionnalité => modifier UNIQUEMENT ce fichier ;
le menu (routing), le guide, les plans Alice et les tarifs se mettent à jour.

Champ `audience` (optionnel, défaut "all") : à qui s'adresse la fonctionnalité.
  - "all"          : commune aux deux profils gestionnaire (propriétaire ET mandataire) ;
  - "mandataire"   : réservée au gestionnaire mandataire (gestion pour compte de tiers) ;
  - "proprietaire" : réservée au gestionnaire propriétaire (gère son propre patrimoine).
Alice s'en sert pour proposer DEUX listes de fonctionnalités par plan (une par profil).
"""

# Catégories d'affichage (ordre = ordre des sections).
CATEGORY_MISE_EN_LOCATION = "Mise en location"
CATEGORY_GESTION = "Gestion locative"
CATEGORY_FINANCE = "Finance et comptabilité"
CATEGORY_SYNDIC = "Syndic (copropriété)"
CATEGORY_IA = "Assistance"

# Chaque entrée : key (stable), label, description, category, order.
# Les descriptions sont rédigées comme le ferait un gestionnaire immobilier :
# concrètes, orientées bénéfice, sans jargon ni tiret cadratin.
FEATURE_CATALOG: list[dict] = [
    # ── Mise en location ───────────────────────────────────────────────────────
    {
        "key": "diffusion",
        "label": "Publication des annonces",
        "category": CATEGORY_MISE_EN_LOCATION,
        "audience": "proprietaire",
        "description": "Rédigez des annonces attractives (photos, descriptif, critères), diffusez-les sur vos supports en un clic, en publication immédiate ou programmée, et suivez leur audience pour louer plus vite.",
    },
    {
        "key": "candidatures",
        "label": "Gestion des candidatures",
        "category": CATEGORY_MISE_EN_LOCATION,
        "audience": "proprietaire",
        "description": "Recevez et centralisez les dossiers, réclamez les pièces par lien sécurisé, proposez des visites avec réservation en ligne, comparez les profils en toute objectivité et transformez le candidat retenu en locataire.",
    },
    # ── Gestion locative ───────────────────────────────────────────────────────
    {
        "key": "dashboard",
        "label": "Tableau de bord",
        "category": CATEGORY_GESTION,
        "description": "Pilotez votre activité d'un coup d'œil : loyers encaissés, taux d'occupation, impayés et échéances à venir réunis sur un seul écran.",
    },
    {
        "key": "properties",
        "label": "Propriétés",
        "category": CATEGORY_GESTION,
        "description": "Réunissez tout votre patrimoine au même endroit : caractéristiques, adresse, équipements, diagnostics et statut d'occupation de chaque bien.",
    },
    {
        "key": "tenants",
        "label": "Locataires",
        "category": CATEGORY_GESTION,
        "description": "Gardez chaque locataire à portée de main : coordonnées, pièces justificatives, garants et historique complet de la relation.",
    },
    {
        "key": "leases",
        "label": "Contrats",
        "category": CATEGORY_GESTION,
        "description": "Établissez et suivez vos baux : co-titulaires, loyer et charges, dépôt de garantie, dates clés et conditions particulières.",
    },
    {
        "key": "avis_echeances",
        "label": "Avis d'échéances",
        "category": CATEGORY_GESTION,
        "description": "Émettez automatiquement les appels de loyer au rythme du bail, proratisés pour les mois partiels, prêts à transmettre au locataire.",
    },
    {
        "key": "payments",
        "label": "Paiements",
        "category": CATEGORY_GESTION,
        "description": "Suivez chaque règlement en temps réel : encaissements, soldes, avances et relances, pour ne jamais perdre le fil d'un loyer.",
    },
    {
        "key": "quittances",
        "label": "Quittances de loyer",
        "category": CATEGORY_GESTION,
        "description": "Générez les quittances en PDF à votre charte dès qu'un loyer est soldé, et adressez-les au locataire en un geste.",
    },
    {
        "key": "actualisation",
        "label": "Révision des loyers et charges",
        "category": CATEGORY_GESTION,
        "description": "Révisez le loyer selon l'IRL ou à l'amiable, régularisez et réévaluez les provisions de charges, et répercutez la taxe d'enlèvement des ordures ménagères : chaque opération est datée et conservée à l'historique.",
    },
    {
        "key": "automatisation",
        "label": "Communication et automatisation",
        "category": CATEGORY_GESTION,
        "description": "Confiez à la plateforme l'envoi des avis, quittances et relances, personnalisez vos modèles d'e-mails multilingues et soignez votre communication sans y penser.",
    },
    {
        "key": "templates",
        "label": "Atelier de documents",
        "category": CATEGORY_GESTION,
        "description": "Composez vos propres modèles de documents à votre image : logo, en-tête, mentions légales et blocs réutilisables.",
    },
    {
        "key": "incidents",
        "label": "Démarche",
        "category": CATEGORY_GESTION,
        "description": "Centralisez les demandes de vos locataires et les signalements de la résidence, échangez, relancez et clôturez chaque dossier au bon moment.",
    },
    {
        "key": "entretiens",
        "label": "Entretiens",
        "category": CATEGORY_GESTION,
        "description": "Planifiez et suivez les interventions sur vos biens, de la prise de rendez-vous à la réalisation, sans rien laisser passer.",
    },
    {
        "key": "contacts",
        "label": "Carnet d'adresses",
        "category": CATEGORY_GESTION,
        "description": "Gardez sous la main vos artisans, prestataires et interlocuteurs de confiance, prêts à être sollicités.",
    },
    {
        "key": "offres",
        "label": "Offres & Services",
        "category": CATEGORY_GESTION,
        "description": "Proposez à vos locataires des services partenaires (assurance, énergie, internet…) directement depuis leur espace.",
    },
    {
        "key": "documents_caf",
        "label": "Espace CAF",
        "category": CATEGORY_GESTION,
        "description": "Éditez l'attestation de loyer et le formulaire de tiers payant pré-remplis, et ne manquez plus la déclaration de loyer annuelle (de juillet à décembre).",
    },
    {
        "key": "sortie_locataire",
        "label": "Sortie du locataire",
        "category": CATEGORY_GESTION,
        "description": "Accompagnez chaque départ de bout en bout : préavis, état des lieux de sortie comparé à l'entrée, décompte du dépôt de garantie et clôture administrative du dossier.",
    },
    {
        "key": "admin",
        "label": "Gestion des utilisateurs",
        "category": CATEGORY_GESTION,
        "description": "Maîtrisez les comptes et les accès de votre espace : invitez vos collaborateurs et ouvrez un accès dédié à vos propriétaires et à vos locataires.",
    },
    {
        "key": "tampon",
        "label": "Tampon / cachet professionnel",
        "category": CATEGORY_GESTION,
        "audience": "mandataire",
        "description": "Ajoutez votre cachet professionnel à côté de votre signature sur le bail et les documents CAF, pour des documents officiels prêts à transmettre.",
    },
    # ── Finance et comptabilité ────────────────────────────────────────────────
    {
        "key": "finances",
        "label": "Revenus et comptabilité",
        "category": CATEGORY_FINANCE,
        "description": "Suivez vos revenus locatifs et tenez un grand livre clair, par propriétaire et par période, prêt à présenter.",
    },
    {
        "key": "performance_biens",
        "label": "Performance des biens",
        "category": CATEGORY_FINANCE,
        "description": "Mesurez le rendement de chaque bien : loyer théorique face au loyer perçu et taux d'occupation, pour repérer ce qui mérite votre attention.",
    },
    {
        "key": "liasse_fiscale",
        "label": "Liasse fiscale",
        "category": CATEGORY_FINANCE,
        "description": "Préparez sereinement votre déclaration de revenus fonciers : la liasse est constituée à partir de vos données, sans ressaisie.",
    },
    {
        "key": "compta_mandant",
        "label": "Compta mandant et CRG",
        "category": CATEGORY_FINANCE,
        "audience": "mandataire",
        "description": "Gérez la relation mandataire : honoraires de gestion configurables (taux et TVA), suivi des reversements aux propriétaires et compte rendu de gestion en PDF, à la périodicité de votre choix.",
    },
    # ── Syndic (copropriété) ───────────────────────────────────────────────────
    {
        "key": "syndic",
        "label": "Syndic de copropriété",
        "category": CATEGORY_SYNDIC,
        "audience": "mandataire",
        "description": "Administrez vos copropriétés : lots et clés de répartition (tantièmes), budget prévisionnel, appels de fonds ventilés et comptes des copropriétaires.",
    },
    # ── Assistance ─────────────────────────────────────────────────────────────
    {
        "key": "agents_ia",
        "label": "Agents IA",
        "category": CATEGORY_IA,
        "description": "Appuyez-vous sur une équipe d'agents IA (Comptable, Sécurité, Administratif) joignable sur Telegram pour vos rappels, vos questions et vos consignes.",
    },
]

# Clés canoniques (set) dérivées du catalogue.
FEATURE_KEYS = {f["key"] for f in FEATURE_CATALOG}

# Clés dans l'ordre du catalogue (pour produire des listes ordonnées).
FEATURE_KEYS_ORDERED = [f["key"] for f in FEATURE_CATALOG]

# Audience par clé (défaut "all"). Source de vérité du périmètre par profil.
AUDIENCE_BY_KEY = {f["key"]: f.get("audience", "all") for f in FEATURE_CATALOG}


def allowed_keys_for_profile(profile: str) -> set[str]:
    """Clés autorisées pour un profil gestionnaire ("proprietaire"/"mandataire").

    Une clé est autorisée si son audience vaut "all" ou correspond au profil. Sert
    à garantir qu'un gestionnaire propriétaire n'obtient jamais une fonctionnalité
    réservée au mandataire (et inversement), quel que soit l'état du plan."""
    return {k for k, a in AUDIENCE_BY_KEY.items() if a == "all" or a == profile}


def public_catalog() -> list[dict]:
    """Catalogue sérialisable (avec ordre) pour l'API publique."""
    return [
        {
            "key": f["key"],
            "label": f["label"],
            "description": f["description"],
            "category": f["category"],
            "audience": f.get("audience", "all"),
            "order": i,
        }
        for i, f in enumerate(FEATURE_CATALOG)
    ]
