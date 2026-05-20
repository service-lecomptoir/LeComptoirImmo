import { apiClient } from './client'
import type { Property, PropertyListItem, Unit } from '@/types/property'
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

  listUnits: (id: string) =>
    apiClient.get<Unit[]>(`/properties/${id}/units`),

  getOccupancy: (id: string) =>
    apiClient.get<{ total: number; occupied: number; vacant: number; rate: number }>(
      `/properties/${id}/occupancy`
    ),
}

export const unitsApi = {
  list: (params?: { property_id?: string; available_only?: boolean }) =>
    apiClient.get<Unit[]>('/units', { params }),

  get: (id: string) =>
    apiClient.get<Unit>(`/units/${id}`),

  create: (data: Partial<Unit>) =>
    apiClient.post<Unit>('/units', data),

  update: (id: string, data: Partial<Unit>) =>
    apiClient.put<Unit>(`/units/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/units/${id}`),
}
