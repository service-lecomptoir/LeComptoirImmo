import { apiClient } from './client'

export interface SubscriptionInfo {
  plan_name: string | null
  is_blocked: boolean
  property_limit: number | null
  property_count: number
  can_create_property: boolean
  access_until: string | null
  resiliation_days_remaining: number | null
  /** Fonctionnalités autorisées par le plan ; null = toutes autorisées. */
  features: string[] | null
}

export interface SubscriptionInvoice {
  id: string
  period_year: number
  period_month: number
  amount: number
  plan_name: string | null
  status: 'paid' | 'unpaid'
  paid_at: string | null
  created_at: string
}

export const subscriptionApi = {
  get: () => apiClient.get<SubscriptionInfo>('/subscription'),
  requestResiliation: (reason: string) =>
    apiClient.post('/subscription/resiliation', { reason }),
  invoices: () => apiClient.get<SubscriptionInvoice[]>('/subscription/invoices'),
  downloadInvoice: (id: string) =>
    apiClient.get(`/subscription/invoices/${id}/pdf`, { responseType: 'blob' }),
}
