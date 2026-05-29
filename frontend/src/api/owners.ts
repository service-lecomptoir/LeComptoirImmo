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

  /** Fiche propriétaire liée au compte connecté (null si aucune). */
  me: () =>
    apiClient.get<Owner | null>('/owners/me'),

  /** Met à jour ma propre fiche (coordonnées + RIB). */
  updateMe: (data: Partial<OwnerCreate>) =>
    apiClient.patch<Owner>('/owners/me', data),

  /** Finances d'un propriétaire (revenus, performance biens, fiscal) pour une année. */
  finances: (id: string, year: number) =>
    apiClient.get<OwnerFinances>(`/owners/${id}/finances`, { params: { year } }),

  /** Télécharge la liasse fiscale PDF d'un propriétaire. */
  fiscalPdf: async (id: string, year: number, filename: string) => {
    const r = await apiClient.get(`/owners/${id}/fiscal/pdf`, { params: { year }, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([r.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

export interface OwnerFinancesLine {
  period_label: string
  period_month: number
  property_name: string
  tenant_full_name: string
  amount_due: number
  amount_paid: number
  status: string
  payment_date?: string | null
}
export interface OwnerFinancesBien {
  property_id: string
  property_name: string
  city: string
  rent: number
  charges: number
  total_du: number
  total_percu: number
  is_occupied: boolean
}
export interface OwnerFinances {
  owner_id: string
  owner_name: string
  year: number
  revenus: { total_du: number; total_percu: number; lignes: OwnerFinancesLine[] }
  biens: OwnerFinancesBien[]
  fiscal: { loyers: number; charges: number; apl: number; total_du: number; total_percu: number }
}
