import { apiClient } from './client'

export interface IrlIndexItem {
  id: string
  year: number
  quarter: number
  value: number
  source: string
}

export interface RevisionRow {
  lease_id: string
  tenant_full_name: string
  property_name: string
  owner_id: string | null
  owner_name: string
  current_rent: number
  charges: number
  irl_quarter: number | null
  base_index: number | null
  latest_index_year: number | null
  latest_index_value: number | null
  proposed_rent: number | null
  next_revision_date: string
  revision_due: boolean
  start_date: string
}

export const actualisationApi = {
  listIrl: () => apiClient.get<IrlIndexItem[]>('/actualisation/irl'),
  addIrl: (data: { year: number; quarter: number; value: number }) =>
    apiClient.post<IrlIndexItem>('/actualisation/irl', data),
  refreshIrl: () =>
    apiClient.post<{ fetched: number; configured: boolean; message: string }>('/actualisation/irl/refresh'),

  listRevisions: () => apiClient.get<RevisionRow[]>('/actualisation/loyers'),
  setReference: (leaseId: string, data: { irl_quarter: number; irl_base_index: number }) =>
    apiClient.patch<RevisionRow>(`/actualisation/loyers/${leaseId}/reference`, data),
  applyRevision: (leaseId: string) =>
    apiClient.post<RevisionRow>(`/actualisation/loyers/${leaseId}/appliquer`),
}
