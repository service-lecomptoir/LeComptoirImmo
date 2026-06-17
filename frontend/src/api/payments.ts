import { apiClient } from './client'
import { downloadBlob } from '@/utils/download'
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

  validateDeclaration: (id: string) =>
    apiClient.post<Payment>(`/payments/${id}/validate-declaration`),

  refuseDeclaration: (id: string) =>
    apiClient.post<Payment>(`/payments/${id}/refuse-declaration`),

  delete: (id: string) =>
    apiClient.delete(`/payments/${id}`),

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
    downloadBlob(response.data, filename)
  },

  sendQuittance: (id: string) =>
    apiClient.post<{ id: string; quittance_generated_at: string; quittance_sent_at: string }>(
      `/payments/${id}/quittance/send`
    ),

  // ── Documents générés à la volée, côté locataire ──────────────────────────
  locataireRegularizations: () =>
    apiClient.get<Array<{ id: string; period_start: string | null; period_end: string | null; balance: number; applied_at: string | null }>>(
      '/payments/locataire/regularizations'
    ),

  downloadRegularizationPdf: async (regId: string, filename: string) => {
    const response = await apiClient.get(`/payments/locataire/regularizations/${regId}/pdf`, {
      responseType: 'blob',
    })
    downloadBlob(response.data, filename)
  },

  locataireRevisions: () =>
    apiClient.get<Array<{ lease_id: string; property_name: string | null; last_revision_date: string | null }>>(
      '/payments/locataire/revisions'
    ),

  downloadRevisionPdf: async (leaseId: string, filename: string) => {
    const response = await apiClient.get(`/payments/locataire/revisions/${leaseId}/pdf`, {
      responseType: 'blob',
    })
    downloadBlob(response.data, filename)
  },
}

export const lettersApi = {
  downloadRelance: async (paymentId: string, filename: string) => {
    const response = await apiClient.get(`/letters/relance/${paymentId}`, {
      responseType: 'blob',
    })
    downloadBlob(response.data, filename)
  },

  downloadPlanApurement: async (
    paymentId: string,
    params: { installments: number; first_date: string },
    filename: string,
  ) => {
    const response = await apiClient.get(`/letters/plan-apurement/${paymentId}`, {
      params,
      responseType: 'blob',
    })
    downloadBlob(response.data, filename)
  },

  downloadAttestationCaf: async (leaseId: string, filename: string) => {
    const response = await apiClient.get(`/letters/attestation-caf/${leaseId}`, {
      responseType: 'blob',
    })
    downloadBlob(response.data, filename)
  },

  downloadVersementDirect: async (leaseId: string, filename: string) => {
    const response = await apiClient.get(`/letters/versement-direct/${leaseId}`, {
      responseType: 'blob',
    })
    downloadBlob(response.data, filename)
  },
}
