import { apiClient } from './client'
import type { Tenant, TenantCreate, TenantListItem, PaginatedResponse } from '@/types/tenant'

export const tenantsApi = {
  list: (params?: { search?: string; skip?: number; limit?: number; available_only?: boolean }) =>
    apiClient.get<PaginatedResponse<TenantListItem>>('/tenants', { params }),

  get: (id: string) =>
    apiClient.get<Tenant>(`/tenants/${id}`),

  create: (data: TenantCreate) =>
    apiClient.post<Tenant>('/tenants', data),

  update: (id: string, data: Partial<TenantCreate>) =>
    apiClient.put<Tenant>(`/tenants/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/tenants/${id}`),

  listDocuments: (id: string) =>
    apiClient.get(`/tenants/${id}/documents`),
}
