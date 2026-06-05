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

export interface BillingStatus {
  stripe_enabled: boolean
  has_subscription: boolean
  status: string | null
  current_period_end: string | null
  payment_method_type: string | null
  plan_name: string | null
  monthly_price: number | null
}

export interface AvailablePlan {
  id: string
  name: string
  monthly_price: number
  property_limit: number | null
}

export interface StripePayment {
  id: string
  number: string | null
  created: number
  amount: number
  currency: string
  status: string
  hosted_invoice_url: string | null
  invoice_pdf: string | null
}

export const subscriptionApi = {
  get: () => apiClient.get<SubscriptionInfo>('/subscription'),
  requestResiliation: (reason: string) =>
    apiClient.post('/subscription/resiliation', { reason }),
  invoices: () => apiClient.get<SubscriptionInvoice[]>('/subscription/invoices'),
  downloadInvoice: (id: string) =>
    apiClient.get(`/subscription/invoices/${id}/pdf`, { responseType: 'blob' }),
  // ── Stripe (carte / prélèvement SEPA) ──
  billing: () => apiClient.get<BillingStatus>('/subscription/billing'),
  checkout: () => apiClient.post<{ url: string }>('/subscription/checkout'),
  portal: () => apiClient.post<{ url: string }>('/subscription/portal'),
  availablePlans: () => apiClient.get<AvailablePlan[]>('/subscription/plans'),
  changePlan: (planId: string) =>
    apiClient.post<{ status: string; plan_name: string }>('/subscription/change-plan', { plan_id: planId }),
  payments: () => apiClient.get<StripePayment[]>('/subscription/payments'),
}
