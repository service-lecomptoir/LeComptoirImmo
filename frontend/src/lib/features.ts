/**
 * Entitlements par plan tarifaire (côté LeComptoir Immo).
 *
 * Le plan Alice définit les fonctionnalités autorisées (clés). On les récupère
 * via /subscription puis on masque le menu et on garde les routes en conséquence.
 *
 * Convention : `features === null` ⇒ aucune restriction (toutes autorisées).
 * Les clés sont le miroir de alice/frontend/src/constants/features.ts.
 */

/** Préfixe de route → clé de fonctionnalité. Ordre = préférence d'atterrissage. */
export const PATH_FEATURES: [string, string][] = [
  ['/dashboard', 'dashboard'],
  ['/properties', 'properties'],
  ['/tenants', 'tenants'],
  ['/leases', 'leases'],
  ['/avis-echeances', 'avis_echeances'],
  ['/payments', 'payments'],
  ['/quittances', 'quittances'],
  ['/actualisation', 'actualisation'],
  ['/automatisation', 'automatisation'],
  ['/templates', 'templates'],
  ['/diffusion', 'diffusion'],
  ['/candidatures', 'candidatures'],
  ['/incidents', 'incidents'],
  ['/signalements', 'incidents'],
  ['/entretiens', 'entretiens'],
  ['/contacts', 'contacts'],
  ['/offres', 'offres'],
  ['/documents-caf', 'documents_caf'],
  ['/sorties', 'sortie_locataire'],
  ['/admin', 'admin'],
  ['/finances/revenus', 'finances'],
  // « /comptabilite/mandant » AVANT « /comptabilite » (le 1er préfixe qui matche gagne).
  ['/comptabilite/mandant', 'compta_mandant'],
  ['/comptabilite', 'finances'],
  ['/coproprietes', 'syndic'],
  ['/finances/biens', 'performance_biens'],
  ['/finances/fiscal', 'liasse_fiscale'],
  ['/proprietaire/revenus', 'finances'],
  ['/proprietaire/biens', 'performance_biens'],
  ['/proprietaire/fiscal', 'liasse_fiscale'],
]

/** Clé de fonctionnalité d'un chemin (null = non gérée → toujours autorisée). */
export function featureForPath(pathname: string): string | null {
  for (const [prefix, feat] of PATH_FEATURES) {
    if (pathname === prefix || pathname.startsWith(prefix + '/')) return feat
  }
  return null
}

/** Vrai si la fonctionnalité est autorisée (null/clé absente = autorisé). */
export function isFeatureAllowed(features: string[] | null, key: string | null): boolean {
  if (!key) return true
  if (features === null) return true
  return features.includes(key)
}

/** Libellés lisibles des fonctionnalités.
 *  REPLI hors-ligne : la source de vérité est le catalogue Immo exposé par
 *  GET /api/v1/public/features (cf. store/catalogStore.ts). Aligné sur
 *  backend/app/core/feature_catalog.py ; même ordre. */
export const FEATURE_LABELS: Record<string, string> = {
  diffusion: 'Publication des annonces',
  candidatures: 'Gestion des candidatures',
  dashboard: 'Tableau de bord',
  properties: 'Propriétés',
  tenants: 'Locataires',
  leases: 'Contrats',
  avis_echeances: "Avis d'échéances",
  payments: 'Paiements',
  quittances: 'Quittances de loyer',
  actualisation: 'Révision des loyers et charges',
  automatisation: 'Communication et automatisation',
  templates: 'Atelier de documents',
  incidents: 'Démarche',
  entretiens: 'Entretiens',
  contacts: "Carnet d'adresses",
  offres: 'Offres & Services',
  documents_caf: 'Espace CAF',
  sortie_locataire: 'Sortie du locataire',
  admin: 'Gestion des utilisateurs',
  tampon: 'Tampon / cachet professionnel',
  finances: 'Revenus et comptabilité',
  performance_biens: 'Performance des biens',
  liasse_fiscale: 'Liasse fiscale',
  compta_mandant: 'Compta mandant et CRG',
  syndic: 'Syndic de copropriété',
  agents_ia: 'Agents IA',
}

/** Descriptions des fonctionnalités (repli hors-ligne ; source = /public/features). */
export const FEATURE_DESCRIPTIONS: Record<string, string> = {
  diffusion: "Rédigez des annonces attractives (photos, descriptif, critères), diffusez-les sur vos supports en un clic, en publication immédiate ou programmée, et suivez leur audience pour louer plus vite.",
  candidatures: "Recevez et centralisez les dossiers, réclamez les pièces par lien sécurisé, proposez des visites avec réservation en ligne, comparez les profils en toute objectivité et transformez le candidat retenu en locataire.",
  dashboard: "Pilotez votre activité d'un coup d'œil : loyers encaissés, taux d'occupation, impayés et échéances à venir réunis sur un seul écran.",
  properties: "Réunissez tout votre patrimoine au même endroit : caractéristiques, adresse, équipements, diagnostics et statut d'occupation de chaque bien.",
  tenants: "Gardez chaque locataire à portée de main : coordonnées, pièces justificatives, garants et historique complet de la relation.",
  leases: "Établissez et suivez vos baux : co-titulaires, loyer et charges, dépôt de garantie, dates clés et conditions particulières.",
  avis_echeances: "Émettez automatiquement les appels de loyer au rythme du bail, proratisés pour les mois partiels, prêts à transmettre au locataire.",
  payments: "Suivez chaque règlement en temps réel : encaissements, soldes, avances et relances, pour ne jamais perdre le fil d'un loyer.",
  quittances: "Générez les quittances en PDF à votre charte dès qu'un loyer est soldé, et adressez-les au locataire en un geste.",
  actualisation: "Révisez le loyer selon l'IRL ou à l'amiable, régularisez et réévaluez les provisions de charges, et répercutez la taxe d'enlèvement des ordures ménagères : chaque opération est datée et conservée à l'historique.",
  automatisation: "Confiez à la plateforme l'envoi des avis, quittances et relances, personnalisez vos modèles d'e-mails multilingues et soignez votre communication sans y penser.",
  templates: "Composez vos propres modèles de documents à votre image : logo, en-tête, mentions légales et blocs réutilisables.",
  incidents: "Centralisez les demandes de vos locataires et les signalements de la résidence, échangez, relancez et clôturez chaque dossier au bon moment.",
  entretiens: "Planifiez et suivez les interventions sur vos biens, de la prise de rendez-vous à la réalisation, sans rien laisser passer.",
  contacts: "Gardez sous la main vos artisans, prestataires et interlocuteurs de confiance, prêts à être sollicités.",
  offres: "Proposez à vos locataires des services partenaires (assurance, énergie, internet…) directement depuis leur espace.",
  documents_caf: "Éditez l'attestation de loyer et le formulaire de tiers payant pré-remplis, et ne manquez plus la déclaration de loyer annuelle (de juillet à décembre).",
  sortie_locataire: "Accompagnez chaque départ de bout en bout : préavis, état des lieux de sortie comparé à l'entrée, décompte du dépôt de garantie et clôture administrative du dossier.",
  admin: "Maîtrisez les comptes et les accès de votre espace : invitez vos collaborateurs et ouvrez un accès dédié à vos propriétaires et à vos locataires.",
  tampon: "Ajoutez votre cachet professionnel à côté de votre signature sur le bail et les documents CAF, pour des documents officiels prêts à transmettre.",
  finances: "Suivez vos revenus locatifs et tenez un grand livre clair, par propriétaire et par période, prêt à présenter.",
  performance_biens: "Mesurez le rendement de chaque bien : loyer théorique face au loyer perçu et taux d'occupation, pour repérer ce qui mérite votre attention.",
  liasse_fiscale: "Préparez sereinement votre déclaration de revenus fonciers : la liasse est constituée à partir de vos données, sans ressaisie.",
  compta_mandant: "Gérez la relation mandataire : honoraires de gestion configurables (taux et TVA), suivi des reversements aux propriétaires et compte rendu de gestion en PDF, à la périodicité de votre choix.",
  syndic: "Administrez vos copropriétés : lots et clés de répartition (tantièmes), budget prévisionnel, appels de fonds ventilés et comptes des copropriétaires.",
  agents_ia: "Appuyez-vous sur une équipe d'agents IA (Comptable, Sécurité, Administratif) joignable sur Telegram pour vos rappels, vos questions et vos consignes.",
}

/** Première route autorisée (cible de repli quand l'actuelle est bloquée). */
export function firstAllowedPath(features: string[] | null): string {
  if (features === null) return '/dashboard'
  for (const [prefix, feat] of PATH_FEATURES) {
    if (features.includes(feat)) return prefix
  }
  return '/abonnement'
}
