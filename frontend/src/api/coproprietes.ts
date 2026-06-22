import { apiClient } from './client'

export interface CoproListItem {
  id: string
  ref_code?: string | null
  name: string
  city?: string | null
  immatriculation?: string | null
  lot_count: number
  created_at: string
}

export interface RepartitionKey {
  id: string
  name: string
  total_tantiemes: number
  is_general: boolean
  position: number
  assigned_tantiemes: number
  balanced: boolean
}

export interface CoproLot {
  id: string
  numero: string
  lot_type?: string | null
  floor?: string | null
  description?: string | null
  owner_id?: string | null
  owner_name?: string | null
  property_id?: string | null
  tantiemes: Record<string, number> // key_id -> valeur
}

export interface CoproDetail {
  id: string
  ref_code?: string | null
  name: string
  immatriculation?: string | null
  address?: string | null
  zip_code?: string | null
  city?: string | null
  country?: string | null
  construction_year?: number | null
  notes?: string | null
  keys: RepartitionKey[]
  lots: CoproLot[]
  created_at: string
  updated_at: string
}

export interface CoproInput {
  name: string
  immatriculation?: string | null
  address?: string | null
  zip_code?: string | null
  city?: string | null
  country?: string | null
  construction_year?: number | null
  notes?: string | null
}

export interface KeyInput {
  name: string
  total_tantiemes: number
  is_general?: boolean
  position?: number
}

export interface LotInput {
  numero: string
  lot_type?: string | null
  floor?: string | null
  description?: string | null
  owner_id?: string | null
  property_id?: string | null
  tantiemes: { key_id: string; tantiemes: number }[]
}

export const coproApi = {
  list: () => apiClient.get<CoproListItem[]>('/coproprietes'),
  get: (id: string) => apiClient.get<CoproDetail>(`/coproprietes/${id}`),
  create: (data: CoproInput) => apiClient.post<CoproDetail>('/coproprietes', data),
  update: (id: string, data: Partial<CoproInput>) => apiClient.put<CoproDetail>(`/coproprietes/${id}`, data),
  delete: (id: string) => apiClient.delete(`/coproprietes/${id}`),

  addKey: (id: string, data: KeyInput) => apiClient.post<RepartitionKey>(`/coproprietes/${id}/keys`, data),
  updateKey: (id: string, keyId: string, data: Partial<KeyInput>) => apiClient.put<RepartitionKey>(`/coproprietes/${id}/keys/${keyId}`, data),
  deleteKey: (id: string, keyId: string) => apiClient.delete(`/coproprietes/${id}/keys/${keyId}`),

  createLot: (id: string, data: LotInput) => apiClient.post<CoproLot>(`/coproprietes/${id}/lots`, data),
  updateLot: (id: string, lotId: string, data: Partial<LotInput>) => apiClient.put<CoproLot>(`/coproprietes/${id}/lots/${lotId}`, data),
  deleteLot: (id: string, lotId: string) => apiClient.delete(`/coproprietes/${id}/lots/${lotId}`),
}
