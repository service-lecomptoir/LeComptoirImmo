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
  ['/incidents', 'incidents'],
  ['/entretiens', 'entretiens'],
  ['/contacts', 'contacts'],
  ['/offres', 'offres'],
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
  actualisation: 'Actualisation loyers et charges',
  automatisation: 'Automatisation',
  templates: 'Ma papeterie',
  incidents: 'Messages et Incidents',
  entretiens: 'Entretiens',
  contacts: "Carnet d'adresses",
  offres: 'Offres & Services',
  admin: 'Administration',
  finances: 'Mes finances',
  performance_biens: 'Performance bien',
  liasse_fiscale: 'Liasse fiscale',
}

/** Première route autorisée (cible de repli quand l'actuelle est bloquée). */
export function firstAllowedPath(features: string[] | null): string {
  if (features === null) return '/dashboard'
  for (const [prefix, feat] of PATH_FEATURES) {
    if (features.includes(feat)) return prefix
  }
  return '/abonnement'
}
