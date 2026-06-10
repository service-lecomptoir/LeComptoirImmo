import { apiClient } from './client'

export type CandidatureStatus = 'nouvelle' | 'en_etude' | 'retenue' | 'refusee'

export interface CandidatureDoc {
  key: string
  provided: boolean
  verified: boolean
}

export interface CandidatureMetrics {
  effort_ratio: number | null
  completeness_pct: number
  docs_provided: number
  docs_verified: number
  docs_total: number
  score: number
}

export interface Candidature {
  id: string
  property_id: string
  full_name: string
  email?: string | null
  phone?: string | null
  employment?: string | null
  monthly_income?: number | null
  has_guarantor: boolean
  message?: string | null
  status: CandidatureStatus
  docs: CandidatureDoc[]
  notes?: string | null
  source: 'annonce' | 'manuel' | string
  created_at: string
  metrics: CandidatureMetrics
}

export interface CandidatureCreate {
  property_id: string
  full_name: string
  email?: string | null
  phone?: string | null
  employment?: string | null
  monthly_income?: number | null
  has_guarantor?: boolean
  message?: string | null
}

export interface CandidatureUpdate {
  full_name?: string
  email?: string | null
  phone?: string | null
  employment?: string | null
  monthly_income?: number | null
  has_guarantor?: boolean
  message?: string | null
  status?: CandidatureStatus
  docs?: CandidatureDoc[]
  notes?: string | null
}

export const candidaturesApi = {
  list: (params?: { property_id?: string; status?: string }) =>
    apiClient.get<Candidature[]>('/candidatures', { params }),
  get: (id: string) => apiClient.get<Candidature>(`/candidatures/${id}`),
  create: (data: CandidatureCreate) => apiClient.post<Candidature>('/candidatures', data),
  update: (id: string, data: CandidatureUpdate) =>
    apiClient.patch<Candidature>(`/candidatures/${id}`, data),
  remove: (id: string) => apiClient.delete(`/candidatures/${id}`),
  docKeys: () => apiClient.get<{ key: string; label: string }[]>('/candidatures/doc-keys'),
  compare: (propertyId: string) =>
    apiClient.get<{ rent_reference: number | null; candidates: Candidature[] }>(
      `/candidatures/compare/${propertyId}`,
    ),
}
