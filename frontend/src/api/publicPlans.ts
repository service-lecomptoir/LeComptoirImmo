import { apiClient } from './client'

/** Plan tarifaire exposé publiquement (page Tarification de l'accueil). */
export interface PublicPlan {
  id: string
  name: string
  description: string | null
  property_limit: number | null
  monthly_price: number
  /** Fonctionnalités incluses ; null = toutes. */
  features: string[] | null
}

export const publicPlansApi = {
  list: () => apiClient.get<PublicPlan[]>('/public/plans'),
}
