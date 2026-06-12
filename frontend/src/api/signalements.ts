import { apiClient } from './client'

export type SignalementCategory = 'bruit' | 'securite' | 'proprete' | 'logement' | 'degradation' | 'autre'
export type SignalementUrgency = 'faible' | 'moyen' | 'urgent'
export type SignalementStatus = 'nouveau' | 'en_cours' | 'resolu' | 'clos'
export type SignalementSource = 'locataire' | 'gestionnaire' | 'telematique'

export interface Signalement {
  id: string
  category: SignalementCategory
  category_label: string
  urgency: SignalementUrgency
  urgency_label: string
  status: SignalementStatus
  status_label: string
  source: SignalementSource
  source_label: string
  title: string | null
  description: string
  occurred_at: string | null
  night_noise: boolean
  photo_url: string | null
  property_id: string | null
  property_name: string | null
  property_address: string | null
  tenant_id: string | null
  tenant_name: string | null
  lease_id: string | null
  resolution_note: string | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface SignalementAlert {
  id: string
  alert_type: 'nocturne' | 'escalade' | 'preventif'
  alert_label: string
  property_id: string | null
  property_name: string | null
  message: string | null
  created_at: string
}

export interface ProblemProperty {
  property_id: string
  property_name: string
  property_address: string | null
  total: number
  ouverts: number
  bruit: number
  urgents: number
}

export interface SignalementCreatePayload {
  category: SignalementCategory
  description: string
  urgency?: SignalementUrgency
  title?: string | null
  occurred_at?: string | null
  property_id?: string | null
  tenant_id?: string | null
  lease_id?: string | null
}

export interface SignalementUpdatePayload {
  status?: SignalementStatus
  urgency?: SignalementUrgency
  resolution_note?: string | null
}

export interface ListParams {
  status?: string
  category?: string
  urgency?: string
  property_id?: string
  limit?: number
  offset?: number
}

export const signalementsApi = {
  // Locataire
  mine: () => apiClient.get<Signalement[]>('/signalements/mine'),
  create: (data: SignalementCreatePayload) => apiClient.post<{ id: string; status: string }>('/signalements', data),
  uploadPhoto: (id: string, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiClient.post<{ photo_url: string }>(`/signalements/${id}/photo`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  // Gestionnaire
  list: (params?: ListParams) => apiClient.get<{ total: number; items: Signalement[] }>('/signalements', { params }),
  get: (id: string) => apiClient.get<Signalement>(`/signalements/${id}`),
  update: (id: string, data: SignalementUpdatePayload) => apiClient.patch<Signalement>(`/signalements/${id}`, data),
  problemProperties: () => apiClient.get<ProblemProperty[]>('/signalements/problem-properties'),
  alerts: () => apiClient.get<SignalementAlert[]>('/signalements/alerts'),
  exportUrl: '/signalements/export',
}
