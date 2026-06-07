import { apiClient } from './client'

export interface SejourManager {
  id: string
  email: string
  full_name: string
  phone?: string | null
  role: string
  is_active: boolean
}

export interface SejourStats {
  managers: number
  active_managers: number
  units: number
  reservations: number
}

export const sejourApi = {
  stats: () => apiClient.get<SejourStats>('/sejour/stats'),
  list: () => apiClient.get<SejourManager[]>('/sejour/managers'),
  create: (data: { email: string; full_name: string; phone?: string; password: string }) =>
    apiClient.post<SejourManager>('/sejour/managers', data),
  update: (id: string, data: Partial<{ full_name: string; phone: string; is_active: boolean }>) =>
    apiClient.patch<SejourManager>(`/sejour/managers/${id}`, data),
  resetPassword: (id: string, new_password: string) =>
    apiClient.post(`/sejour/managers/${id}/reset-password`, { new_password }),
}
