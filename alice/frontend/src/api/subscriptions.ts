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

  /** Traite une demande de résiliation : programme la désactivation du compte. */
  deactivateAccount: (id: string) =>
    apiClient.post<{ found_account: boolean; scheduled_until: string | null; blocked_now: boolean }>(
      `/subscription-requests/${id}/deactivate-account`,
    ),

  /** Supprime définitivement une demande. */
  remove: (id: string) =>
    apiClient.delete(`/subscription-requests/${id}`),
}
