import { apiClient } from './client'

export type CandidatureStatus = 'nouvelle' | 'documents_demandes' | 'en_etude' | 'retenue' | 'refusee'

export interface CandidatureDoc {
  key: string
  label?: string
  required?: boolean
  provided: boolean
  verified: boolean
  filename?: string | null
  uploaded_at?: string | null
  has_file?: boolean
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
  upload_token?: string | null
  upload_url?: string | null
  property_ref?: string | null
  visit_url?: string | null
  visit_invited?: boolean
  visit_slot_id?: string | null
  visit_booked_at?: string | null
  metrics: CandidatureMetrics
}

export interface VisitSlot {
  id: string
  property_id: string
  starts_at: string
  duration_min: number
  capacity: number
  notes?: string | null
  booked_count: number
  remaining: number
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
  requestDocuments: (id: string, data: { doc_keys: string[]; message?: string | null }) =>
    apiClient.post<Candidature & { upload_url: string; email_sent: boolean }>(
      `/candidatures/${id}/request-documents`, data,
    ),
  docDownloadUrl: (id: string, key: string) => `/candidatures/${id}/documents/${key}/download`,

  // Visites
  visitSlots: (propertyId: string) =>
    apiClient.get<VisitSlot[]>('/candidatures/visit-slots', { params: { property_id: propertyId } }),
  createVisitSlot: (data: { property_id: string; starts_at: string; duration_min?: number; capacity?: number; notes?: string }) =>
    apiClient.post<VisitSlot>('/candidatures/visit-slots', data),
  deleteVisitSlot: (slotId: string) => apiClient.delete(`/candidatures/visit-slots/${slotId}`),
  inviteVisit: (id: string, data: { message?: string | null }) =>
    apiClient.post<Candidature & { visit_url: string; email_sent: boolean }>(
      `/candidatures/${id}/invite-visit`, data,
    ),
  accept: (id: string, data: { message?: string | null }) =>
    apiClient.post<Candidature & { email_sent: boolean }>(`/candidatures/${id}/accept`, data),
  acknowledge: (id: string, data: { message?: string | null } = {}) =>
    apiClient.post<Candidature & { email_sent: boolean }>(`/candidatures/${id}/acknowledge`, data),
  remindVisit: (id: string) =>
    apiClient.post<Candidature & { email_sent: boolean }>(`/candidatures/${id}/remind-visit`),
}
