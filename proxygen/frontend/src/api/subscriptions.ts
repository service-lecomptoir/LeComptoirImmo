import { apiClient } from './client'

export interface SubscriptionRequest {
  id: string
  full_name: string
  email: string
  phone?: string | null
  company?: string | null
  message?: string | null
  source: string
  status: 'nouveau' | 'en_cours' | 'traite' | 'rejete'
  notes?: string | null
  created_at: string
  processed_at?: string | null
}

export interface SubscriptionStats {
  nouveau: number
  en_cours: number
  traite: number
  rejete: number
  total: number
}

export const subscriptionsApi = {
  list: (status?: string) =>
    apiClient.get<SubscriptionRequest[]>('/subscription-requests', {
      params: status ? { status } : undefined,
    }),

  stats: () =>
    apiClient.get<SubscriptionStats>('/subscription-requests/stats'),

  update: (id: string, data: { status?: string; notes?: string }) =>
    apiClient.patch<SubscriptionRequest>(`/subscription-requests/${id}`, data),
}
