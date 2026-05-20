import { apiClient } from './client'
import type { Payment, PaymentListResponse, PaymentStatus, DashboardStats, MonthlyStats } from '@/types/payment'

interface ListParams {
  search?: string
  lease_id?: string
  tenant_id?: string
  status?: PaymentStatus
  year?: number
  month?: number
  skip?: number
  limit?: number
}

interface RecordPaymentData {
  amount_paid: number
  payment_date: string
  payment_method?: string
  notes?: string
}

export const paymentsApi = {
  list: (params?: ListParams) =>
    apiClient.get<PaymentListResponse>('/payments', { params }),

  get: (id: string) =>
    apiClient.get<Payment>(`/payments/${id}`),

  create: (data: { lease_id: string; period_year: number; period_month: number }) =>
    apiClient.post<Payment>('/payments', data),

  record: (id: string, data: RecordPaymentData) =>
    apiClient.post<Payment>(`/payments/${id}/record`, data),

  cancel: (id: string) =>
    apiClient.post<Payment>(`/payments/${id}/cancel`),

  generate: (year: number, month: number) =>
    apiClient.post<{ generated: number; year: number; month: number }>(
      '/payments/generate',
      { year, month }
    ),

  dashboardStats: () =>
    apiClient.get<DashboardStats>('/payments/stats/dashboard'),

  monthlyStats: (year: number, month: number) =>
    apiClient.get<MonthlyStats>('/payments/stats/monthly', { params: { year, month } }),

  downloadQuittance: async (id: string, filename: string) => {
    const response = await apiClient.get(`/payments/${id}/quittance`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

export const lettersApi = {
  downloadRelance: async (paymentId: string, filename: string) => {
    const response = await apiClient.get(`/letters/relance/${paymentId}`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  downloadAttestationCaf: async (leaseId: string, filename: string) => {
    const response = await apiClient.get(`/letters/attestation-caf/${leaseId}`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}
