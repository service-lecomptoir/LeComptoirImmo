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

export interface ChargeLastRegul {
  id: string
  period_start: string
  period_end: string
  provisions_total: number
  real_total: number
  balance: number
  new_monthly_provision: number
  applied_at: string | null
}

export interface ChargeRow {
  lease_id: string
  tenant_full_name: string
  property_name: string
  owner_id: string | null
  owner_name: string
  current_monthly_provision: number
  default_period_start: string
  default_period_end: string
  provisions_paid_12m: number
  last_regularization: ChargeLastRegul | null
}

export interface ChargePreview {
  months_count: number
  provisions_total: number
  real_total: number
  balance: number
  old_monthly_provision: number
  suggested_monthly_provision: number
}

export const actualisationApi = {
  listIrl: () => apiClient.get<IrlIndexItem[]>('/actualisation/irl'),
  addIrl: (data: { year: number; quarter: number; value: number }) =>
    apiClient.post<IrlIndexItem>('/actualisation/irl', data),
  updateIrl: (id: string, data: { year: number; quarter: number; value: number }) =>
    apiClient.patch<IrlIndexItem>(`/actualisation/irl/${id}`, data),
  deleteIrl: (id: string) => apiClient.delete(`/actualisation/irl/${id}`),
  refreshIrl: () =>
    apiClient.post<{ fetched: number; configured: boolean; message: string }>('/actualisation/irl/refresh'),

  listRevisions: () => apiClient.get<RevisionRow[]>('/actualisation/loyers'),
  setReference: (leaseId: string, data: { irl_quarter: number; irl_base_index: number }) =>
    apiClient.patch<RevisionRow>(`/actualisation/loyers/${leaseId}/reference`, data),
  applyRevision: (leaseId: string) =>
    apiClient.post<RevisionRow>(`/actualisation/loyers/${leaseId}/appliquer`),

  listCharges: () => apiClient.get<ChargeRow[]>('/actualisation/charges'),
  previewCharge: (leaseId: string, data: { period_start: string; period_end: string; real_total: number }) =>
    apiClient.post<ChargePreview>(`/actualisation/charges/${leaseId}/preview`, data),
  applyCharge: (leaseId: string, data: { period_start: string; period_end: string; real_total: number; new_monthly_provision: number; notes?: string }) =>
    apiClient.post<ChargeRow>(`/actualisation/charges/${leaseId}/appliquer`, data),
  updateCharge: (regId: string, data: { period_start: string; period_end: string; real_total: number; new_monthly_provision: number; notes?: string }) =>
    apiClient.put<ChargeRow>(`/actualisation/charges/regularizations/${regId}`, data),
  deleteCharge: (regId: string) => apiClient.delete(`/actualisation/charges/regularizations/${regId}`),
}
