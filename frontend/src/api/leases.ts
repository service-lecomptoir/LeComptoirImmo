import { apiClient } from './client'
import { downloadBlob } from '@/utils/download'
import type { Lease, LeaseListResponse } from '@/types/lease'

interface ListParams {
  is_active?: boolean
  property_id?: string
  tenant_id?: string
  search?: string
  skip?: number
  limit?: number
}

interface TerminateData {
  end_date: string
  notice_date?: string
}

export const leasesApi = {
  list: (params?: ListParams) =>
    apiClient.get<LeaseListResponse>('/leases', { params }),

  get: (id: string) =>
    apiClient.get<Lease>(`/leases/${id}`),

  create: (data: unknown) =>
    apiClient.post<Lease>('/leases', data),

  update: (id: string, data: unknown) =>
    apiClient.put<Lease>(`/leases/${id}`, data),

  terminate: (id: string, data: TerminateData) =>
    apiClient.post<Lease>(`/leases/${id}/terminate`, data),

  delete: (id: string) =>
    apiClient.delete(`/leases/${id}`),

  downloadPdf: async (id: string, filename: string) => {
    const response = await apiClient.get(`/leases/${id}/pdf`, {
      responseType: 'blob',
    })
    downloadBlob(response.data, filename)
  },
}
