import { apiClient } from './client'

/** Plan tarifaire exposé publiquement (page Tarification de l'accueil). */
export interface PublicPlan {
  id: string
  name: string
  description: string | null
  property_limit: number | null
  monthly_price: number
  /** Type de gestionnaire ciblé : 'proprietaire' | 'mandataire' | null. */
  manager_type: 'proprietaire' | 'mandataire' | null
  /** Fonctionnalités incluses ; null = toutes (du périmètre du type). */
  features: string[] | null
}

export const publicPlansApi = {
  list: () => apiClient.get<PublicPlan[]>('/public/plans'),
}
