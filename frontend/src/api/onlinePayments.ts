import { apiClient } from './client'

export interface PaymentConfig {
  card_payments_enabled: boolean
  payment_provider: 'stripe' | 'sumup' | null
  stripe: { publishable_key: string; secret_key_set: boolean; webhook_secret_set: boolean; webhook_url: string }
  sumup: { merchant_code: string; api_key_set: boolean }
}

export interface CardAvailability {
  available: boolean
  provider: 'stripe' | 'sumup' | null
}

export interface CheckoutResult {
  provider: 'stripe' | 'sumup'
  url?: string
  checkout_id?: string
  amount?: number
  currency?: string
}

export const onlinePaymentsApi = {
  getConfig: () => apiClient.get<PaymentConfig>('/online-payments/config'),
  putConfig: (data: Record<string, unknown>) =>
    apiClient.put<PaymentConfig>('/online-payments/config', data),
  availability: () =>
    apiClient.get<CardAvailability>('/online-payments/locataire/availability'),
  checkout: (payment_id?: string) =>
    apiClient.post<CheckoutResult>('/online-payments/locataire/checkout', { payment_id }),
  sumupConfirm: (checkout_id: string) =>
    apiClient.post<{ status: string }>('/online-payments/locataire/sumup/confirm', { checkout_id }),
}
