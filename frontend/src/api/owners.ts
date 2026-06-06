import { apiClient } from './client'
import { downloadBlob } from '@/utils/download'
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
    downloadBlob(r.data, filename)
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
  address: string
  rent: number
  charges: number
  total_du: number
  total_percu: number
  annual_rent: number
  active_leases: number
  is_occupied: boolean
}
export interface OwnerFiscal {
  gross_rent_revenue: number
  charges_received: number
  total_gross_revenue: number
  management_fees: number
  total_deductible: number
  net_revenue: number
}
export interface OwnerFinances {
  owner_id: string
  owner_name: string
  year: number
  revenus: { total_du: number; total_percu: number; lignes: OwnerFinancesLine[] }
  biens: OwnerFinancesBien[]
  fiscal: OwnerFiscal
}
