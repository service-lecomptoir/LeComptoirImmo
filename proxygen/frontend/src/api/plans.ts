import { apiClient } from './client'
import type { Plan } from '@/types'

export interface PlanCreateData {
  name: string
  description?: string | null
  property_limit?: number | null
  monthly_price: number
}

export interface PlanUpdateData {
  name?: string
  description?: string | null
  property_limit?: number | null
  monthly_price?: number
  is_active?: boolean
}

export const plansApi = {
  list: () =>
    apiClient.get<Plan[]>('/plans'),

  create: (data: PlanCreateData) =>
    apiClient.post<Plan>('/plans', data),

  update: (id: string, data: PlanUpdateData) =>
    apiClient.patch<Plan>(`/plans/${id}`, data),

  deactivate: (id: string) =>
    apiClient.delete(`/plans/${id}`),
}
