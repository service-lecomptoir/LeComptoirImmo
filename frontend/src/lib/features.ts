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
  ['/entretiens', 'entretiens'],
  ['/contacts', 'contacts'],
  ['/offres', 'offres'],
  ['/documents-caf', 'documents_caf'],
  ['/sorties', 'sortie_locataire'],
  ['/admin', 'admin'],
  ['/finances/revenus', 'finances'],
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

/** Libellés lisibles des fonctionnalités (miroir de alice constants/features.ts).
 *  Utilisés notamment sur la page Tarification publique. */
export const FEATURE_LABELS: Record<string, string> = {
  dashboard: 'Tableau de bord',
  properties: 'Propriétés',
  tenants: 'Locataires',
  leases: 'Contrats',
  avis_echeances: "Avis d'échéances",
  payments: 'Paiements',
  quittances: 'Quittances de loyer',
  actualisation: 'Révision des loyers et charges',
  automatisation: "Règles d'automatisation",
  templates: 'Ma papeterie',
  diffusion: 'Publication des annonces',
  candidatures: 'Gestion des candidatures',
  sortie_locataire: 'Sortie du locataire',
  incidents: 'Démarche',
  entretiens: 'Entretiens',
  contacts: "Carnet d'adresses",
  offres: 'Offres & Services',
  documents_caf: 'Espace CAF',
  admin: 'Gestion des utilisateurs',
  finances: 'Mes revenus',
  performance_biens: 'Performance bien',
  liasse_fiscale: 'Liasse fiscale',
  agents_ia: 'Agents IA',
}

/** Descriptions courtes des fonctionnalités (infobulles, page Tarification). */
export const FEATURE_DESCRIPTIONS: Record<string, string> = {
  dashboard: "Vue d'ensemble : indicateurs clés, revenus et alertes en un coup d'œil.",
  properties: 'Gérez tous vos biens : caractéristiques, adresse, équipements et occupation.',
  tenants: 'Fiches locataires : coordonnées, pièces justificatives et historique.',
  leases: 'Contrats de location : baux, co-titulaires, dates et conditions.',
  avis_echeances: "Génération automatique des avis d'échéance selon la fréquence du bail.",
  payments: 'Suivi des paiements : encaissements, déclarations, relances et soldes.',
  quittances: 'Quittances de loyer en PDF, à votre charte, prêtes à envoyer.',
  actualisation: 'Révision du loyer (IRL ou réévaluation amiable), régularisation et réévaluation des provisions de charges, et décompte de taxes foncières (TEOM).',
  automatisation: 'Automatisation des tâches récurrentes (avis, quittances, relances).',
  templates: 'Vos modèles de documents personnalisés (logo, en-tête, mentions).',
  diffusion: "Création et personnalisation des annonces (photos, description, critères), diffusion sur vos plateformes, publication immédiate ou programmée et suivi des performances (vues).",
  candidatures: "Centralisation des dossiers candidats, vérification des pièces justificatives, analyse et comparaison des profils, aide à la sélection du locataire le plus adapté.",
  sortie_locataire: "Suivi des préavis, état des lieux de sortie comparé à l'entrée, décompte du dépôt de garantie (retenues/restitution) et clôture administrative du dossier.",
  incidents: 'Démarches : demandes de vos locataires, échanges et suivi (relance, clôture).',
  entretiens: 'Planification et suivi des entretiens et interventions sur vos biens.',
  contacts: "Carnet d'adresses : artisans, prestataires et contacts utiles.",
  offres: 'Offres & services partenaires proposés à vos locataires.',
  documents_caf: "Espace CAF : attestation de loyer et formulaire tiers payant, + rappel de déclaration de loyer (juillet→décembre).",
  admin: 'Gestion des comptes utilisateurs et des accès de votre espace.',
  finances: 'Suivi des revenus locatifs par propriétaire et par période.',
  performance_biens: 'Performance par bien : loyer théorique vs perçu, taux d’occupation.',
  liasse_fiscale: 'Génération de la liasse fiscale (revenus fonciers) pour vos déclarations.',
  agents_ia: "Équipe d'agents IA (Comptable, Sécurité, Administratif) accessible par Telegram : rappels, questions et instructions.",
}

/** Première route autorisée (cible de repli quand l'actuelle est bloquée). */
export function firstAllowedPath(features: string[] | null): string {
  if (features === null) return '/dashboard'
  for (const [prefix, feat] of PATH_FEATURES) {
    if (features.includes(feat)) return prefix
  }
  return '/abonnement'
}
