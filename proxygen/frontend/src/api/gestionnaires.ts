import { apiClient } from './client'
import type { Gestionnaire, GestionnaireProperty } from '@/types'

export interface GestionnaireCreateData {
  email: string
  full_name: string
  password: string
  plan_id?: string | null
  property_limit_override?: number | null
  monthly_price_override?: number | null
  notes?: string | null
}

export interface GestionnaireUpdateData {
  email?: string
  full_name?: string
  plan_id?: string | null
  property_limit_override?: number | null
  monthly_price_override?: number | null
  notes?: string | null
}

export const gestionnairesApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<Gestionnaire[]>('/gestionnaires', { params }),

  get: (id: string) =>
    apiClient.get<Gestionnaire>(`/gestionnaires/${id}`),

  create: (data: GestionnaireCreateData) =>
    apiClient.post<Gestionnaire>('/gestionnaires', data),

  update: (id: string, data: GestionnaireUpdateData) =>
    apiClient.patch<Gestionnaire>(`/gestionnaires/${id}`, data),

  block: (id: string) =>
    apiClient.post<Gestionnaire>(`/gestionnaires/${id}/block`),

  unblock: (id: string) =>
    apiClient.post<Gestionnaire>(`/gestionnaires/${id}/unblock`),

  getProperties: (id: string) =>
    apiClient.get<GestionnaireProperty[]>(`/gestionnaires/${id}/properties`),
}
