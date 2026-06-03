import { apiClient } from './client'

export interface Prestataire {
  id: string
  name: string
  specialty?: string
  phone?: string
  email?: string
  siret?: string
  notes?: string
  is_active: boolean
  created_at: string
}

export interface Entretien {
  id: string
  title: string
  description?: string
  type: 'preventif' | 'correctif' | 'inspection'
  status: 'planifie' | 'en_cours' | 'termine' | 'annule'
  frequency: 'unique' | 'mensuel' | 'trimestriel' | 'semestriel' | 'annuel'
  scheduled_date: string
  completed_date?: string
  next_date?: string
  cost?: number
  property_id?: string
  property_label?: string
  prestataire_id?: string
  prestataire_name?: string
  notes?: string
  created_at: string
  updated_at: string
}

export const prestatairesApi = {
  list: (active_only = true) =>
    apiClient.get<Prestataire[]>('/prestataires', { params: { active_only } }),
  create: (data: Omit<Prestataire, 'id' | 'is_active' | 'created_at'>) =>
    apiClient.post<Prestataire>('/prestataires', data),
  update: (id: string, data: Partial<Prestataire>) =>
    apiClient.patch<Prestataire>(`/prestataires/${id}`, data),
  delete: (id: string) =>
    apiClient.delete(`/prestataires/${id}`),
}

export const entretiensApi = {
  list: (params?: { status?: string; property_id?: string; limit?: number }) =>
    apiClient.get<{ total: number; items: Entretien[] }>('/entretiens', { params }),
  create: (data: Omit<Entretien, 'id' | 'created_at' | 'updated_at' | 'property_label' | 'prestataire_name'>) =>
    apiClient.post<{ id: string }>('/entretiens', data),
  get: (id: string) =>
    apiClient.get<Entretien>(`/entretiens/${id}`),
  update: (id: string, data: Partial<Entretien>) =>
    apiClient.patch<Entretien>(`/entretiens/${id}`, data),
  delete: (id: string) =>
    apiClient.delete(`/entretiens/${id}`),
  autoplan: () =>
    apiClient.post<{ created: number; items: { title: string; property_label?: string; scheduled_date: string; cadence_months: number; overdue: boolean }[] }>(
      '/entretiens/autoplan'),
}
