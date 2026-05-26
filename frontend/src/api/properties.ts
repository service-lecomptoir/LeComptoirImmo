import { apiClient } from './client'
import type { Property, PropertyListItem } from '@/types/property'
import type { PaginatedResponse } from '@/types/tenant'

export const propertiesApi = {
  list: (params?: { search?: string; skip?: number; limit?: number }) =>
    apiClient.get<PaginatedResponse<PropertyListItem>>('/properties', { params }),

  get: (id: string) =>
    apiClient.get<Property>(`/properties/${id}`),

  create: (data: Partial<Property>) =>
    apiClient.post<Property>('/properties', data),

  update: (id: string, data: Partial<Property>) =>
    apiClient.put<Property>(`/properties/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/properties/${id}`),

  getOccupancy: (id: string) =>
    apiClient.get<{ total: number; occupied: number; vacant: number; rate: number }>(
      `/properties/${id}/occupancy`
    ),
}
