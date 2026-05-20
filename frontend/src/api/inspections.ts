import { apiClient } from './client'
import type { Inspection, InspectionListResponse } from '@/types/inspection'

interface ListParams {
  lease_id?: string
  unit_id?: string
  skip?: number
  limit?: number
}

export const inspectionsApi = {
  list: (params?: ListParams) =>
    apiClient.get<InspectionListResponse>('/inspections', { params }),

  get: (id: string) =>
    apiClient.get<Inspection>(`/inspections/${id}`),

  create: (data: unknown) =>
    apiClient.post<Inspection>('/inspections', data),

  update: (id: string, data: unknown) =>
    apiClient.put<Inspection>(`/inspections/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/inspections/${id}`),
}
