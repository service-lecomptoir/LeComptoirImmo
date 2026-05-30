import { apiClient } from './client'

export interface Invoice {
  id: string
  gestionnaire_user_id: string
  gestionnaire_name: string | null
  gestionnaire_email: string | null
  period_year: number
  period_month: number
  amount: number
  plan_name: string | null
  status: 'paid' | 'unpaid'
  paid_at: string | null
  created_at: string
}

export interface InvoiceStats {
  paid_count: number
  unpaid_count: number
  paid_amount: number
  unpaid_amount: number
}

export interface InvoiceEdit {
  status?: 'paid' | 'unpaid'
  amount?: number
  plan_name?: string | null
  period_year?: number
  period_month?: number
}

export const invoicesApi = {
  list: (year: number, month: number, status?: string) =>
    apiClient.get<Invoice[]>('/invoices', {
      params: { year, month, ...(status ? { status } : {}) },
    }),

  stats: () => apiClient.get<InvoiceStats>('/invoices/stats'),

  generate: (year: number, month: number) =>
    apiClient.post<Invoice[]>('/invoices/generate', { year, month }),

  update: (id: string, data: InvoiceEdit) =>
    apiClient.patch<Invoice>(`/invoices/${id}`, data),

  remove: (id: string) => apiClient.delete(`/invoices/${id}`),

  downloadPdf: (id: string) =>
    apiClient.get<Blob>(`/invoices/${id}/pdf`, { responseType: 'blob' }),

  sendEmail: (id: string) =>
    apiClient.post<{ sent: boolean; recipient: string; detail?: string }>(`/invoices/${id}/send-email`),
}
