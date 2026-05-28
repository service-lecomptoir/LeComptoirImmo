import { apiClient } from './client'

export interface AvisEcheanceSummary {
  id: string
  period_year: number
  period_month: number
  period_label: string
  period_start?: string | null
  period_end?: string | null
  period_range_label?: string | null
  due_date: string
  amount_total: number
  amount_rent: number
  amount_charges: number
  amount_apl?: number | null
  status: 'brouillon' | 'envoye' | 'acquitte'
  sent_at?: string | null
  is_auto_generated: boolean
  tenant_full_name: string
  property_name: string
  lease_id: string
  tenant_id: string
  notes?: string | null
  pdf_path?: string | null
  generated_by?: string | null
  created_at: string
  updated_at: string
}

export interface GenerateAvisIn {
  lease_id: string
  period_year: number
  period_month: number
  apl_amount_override?: number | null
}

export interface BulkGenerateIn {
  period_year: number
  period_month: number
}

export interface GenerateMonthlyResult {
  generated: number
  period_year: number
  period_month: number
  message: string
}

export const avisEcheancesApi = {
  list(params?: {
    lease_id?: string
    year?: number
    month?: number
    status?: string
    skip?: number
    limit?: number
  }) {
    return apiClient.get<AvisEcheanceSummary[]>('/avis-echeances', { params })
  },

  getById(id: string) {
    return apiClient.get<AvisEcheanceSummary>(`/avis-echeances/${id}`)
  },

  generate(body: GenerateAvisIn) {
    return apiClient.post<AvisEcheanceSummary>('/avis-echeances/generate', body)
  },

  generateMonthly(body: BulkGenerateIn) {
    return apiClient.post<GenerateMonthlyResult>('/avis-echeances/generate-monthly', body)
  },

  markSent(id: string) {
    return apiClient.post<AvisEcheanceSummary>(`/avis-echeances/${id}/send`)
  },

  markAcquitte(id: string) {
    return apiClient.post<AvisEcheanceSummary>(`/avis-echeances/${id}/acquitter`)
  },

  updateApl(id: string, apl_amount: number | null) {
    return apiClient.patch<AvisEcheanceSummary>(`/avis-echeances/${id}/apl`, { apl_amount })
  },

  patch(id: string, body: {
    amount_rent?: number | null
    amount_charges?: number | null
    amount_apl?: number | null
    due_date?: string | null
    notes?: string | null
  }) {
    return apiClient.patch<AvisEcheanceSummary>(`/avis-echeances/${id}`, body)
  },

  relancer(id: string) {
    return apiClient.post<AvisEcheanceSummary>(`/avis-echeances/${id}/relancer`)
  },

  delete(id: string) {
    return apiClient.delete(`/avis-echeances/${id}`)
  },

  pdfUrl(id: string): string {
    const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    return `${base}/api/v1/avis-echeances/${id}/pdf`
  },
}

export interface SchedulerConfig {
  day: number
  hour: number
  minute: number
  next_run: string | null
}

export const schedulerApi = {
  getConfig() {
    return apiClient.get<SchedulerConfig>('/settings/scheduler')
  },
  updateConfig(body: { day: number; hour: number; minute: number }) {
    return apiClient.put<SchedulerConfig>('/settings/scheduler', body)
  },
}
