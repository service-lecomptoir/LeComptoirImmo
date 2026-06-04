/**
 * Catalogue des fonctionnalités d'un plan tarifaire.
 * Les `key` sont la source de vérité partagée avec LeComptoir Immo
 * (stockées dans alice_plans.features, propagées via /internal/license).
 * L'ordre = ordre d'affichage dans le formulaire de plan.
 */
export interface PlanFeature {
  key: string
  label: string
}

export const PLAN_FEATURES: PlanFeature[] = [
  { key: 'dashboard', label: 'Tableau de bord' },
  { key: 'properties', label: 'Propriétés' },
  { key: 'tenants', label: 'Locataires' },
  { key: 'leases', label: 'Contrats' },
  { key: 'avis_echeances', label: "Avis d'échéances" },
  { key: 'payments', label: 'Paiements' },
  { key: 'quittances', label: 'Quittances de loyer' },
  { key: 'actualisation', label: 'Révision des loyers et charges' },
  { key: 'automatisation', label: "Règles d'automatisation" },
  { key: 'templates', label: 'Ma papeterie' },
  { key: 'incidents', label: 'Démarche' },
  { key: 'entretiens', label: 'Entretiens' },
  { key: 'contacts', label: "Carnet d'adresses" },
  { key: 'offres', label: 'Offres & Services' },
  { key: 'documents_caf', label: 'Documents CAF' },
  { key: 'admin', label: 'Gestion des utilisateurs' },
  { key: 'finances', label: 'Mes revenus' },
  { key: 'performance_biens', label: 'Performance bien' },
  { key: 'liasse_fiscale', label: 'Liasse fiscale' },
]

export const ALL_FEATURE_KEYS: string[] = PLAN_FEATURES.map(f => f.key)
