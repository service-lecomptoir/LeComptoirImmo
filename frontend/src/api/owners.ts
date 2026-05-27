import { apiClient } from './client'
import type { Owner, OwnerCreate, OwnerListItem, PaginatedResponse } from '@/types/owner'

export const ownersApi = {
  list: (params?: { search?: string; skip?: number; limit?: number; available_only?: boolean }) =>
    apiClient.get<PaginatedResponse<OwnerListItem>>('/owners', { params }),

  get: (id: string) =>
    apiClient.get<Owner>(`/owners/${id}`),

  create: (data: OwnerCreate) =>
    apiClient.post<Owner>('/owners', data),

  update: (id: string, data: Partial<OwnerCreate>) =>
    apiClient.put<Owner>(`/owners/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/owners/${id}`),

  listDocuments: (id: string) =>
    apiClient.get(`/owners/${id}/documents`),
}
