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

  /** Compte mandant (CRG) : encaissé, honoraires, net, reversé, solde à reverser.
   *  period = mensuel|trimestriel|semestriel|annuel ; index = mois/trimestre/semestre. */
  mandant: (id: string, year: number, period: CrgPeriod = 'annuel', index = 1) =>
    apiClient.get<MandantAccount>(`/owners/${id}/mandant`, { params: { year, period, index } }),

  /** Liste des reversements (optionnellement filtrés par année). */
  reversements: (id: string, year?: number) =>
    apiClient.get<Reversement[]>(`/owners/${id}/reversements`, { params: year ? { year } : {} }),

  /** Enregistre un reversement au propriétaire. */
  createReversement: (id: string, data: ReversementCreate) =>
    apiClient.post<Reversement>(`/owners/${id}/reversements`, data),

  /** Supprime un reversement. */
  deleteReversement: (id: string, reversementId: string) =>
    apiClient.delete(`/owners/${id}/reversements/${reversementId}`),

  /** Télécharge le compte rendu de gestion (CRG) PDF pour la périodicité choisie. */
  crgPdf: async (id: string, year: number, filename: string, period: CrgPeriod = 'annuel', index = 1) => {
    const r = await apiClient.get(`/owners/${id}/crg/pdf`, { params: { year, period, index }, responseType: 'blob' })
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

export interface Reversement {
  id: string
  owner_id: string
  period_year: number
  period_month?: number | null
  amount: number
  method?: string | null
  reversement_date: string
  label?: string | null
  note?: string | null
  created_at: string
}
export interface ReversementCreate {
  period_year: number
  period_month?: number | null
  amount: number
  method?: string | null
  reversement_date: string
  label?: string | null
  note?: string | null
}
export type CrgPeriod = 'mensuel' | 'trimestriel' | 'semestriel' | 'annuel'
export interface MandantAccount {
  owner_id: string
  owner_name: string
  year: number
  period: CrgPeriod
  period_index: number
  period_label: string
  month_start: number
  month_end: number
  honoraires: { rate: number; vat_rate: number; ht: number; vat: number; ttc: number }
  loyers_encaisses: number
  charges_encaissees: number
  total_encaisse: number
  net_proprietaire: number
  total_reverse: number
  solde_a_reverser: number
  reversements: Array<{
    id: string
    period_year: number
    period_month?: number | null
    amount: number
    method?: string | null
    reversement_date: string
    label?: string | null
    note?: string | null
  }>
  revenus: { total_du: number; total_percu: number; lignes: OwnerFinancesLine[] }
  biens: OwnerFinancesBien[]
}
