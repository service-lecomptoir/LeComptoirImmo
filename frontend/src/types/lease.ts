export type LeaseType = 'vide' | 'meuble' | 'mobilite' | 'commercial'
export type PaymentMethod = 'virement' | 'cheque' | 'prelevement' | 'especes'
export type RentCallRule = 'contractuelle' | 'calendrier'
export type PaymentFrequency =
  | 'mensuelle'
  | 'bimestrielle'
  | 'trimestrielle'
  | 'semestrielle'
  | 'annuelle'

export const RENT_CALL_RULE_LABELS: Record<RentCallRule, string> = {
  contractuelle: 'Période contractuelle',
  calendrier: 'Période calendrier',
}

export const PAYMENT_FREQUENCY_LABELS: Record<PaymentFrequency, string> = {
  mensuelle: 'Mensuelle',
  bimestrielle: 'Bimestrielle',
  trimestrielle: 'Trimestrielle',
  semestrielle: 'Semestrielle',
  annuelle: 'Annuelle',
}

export const LEASE_TYPE_LABELS: Record<LeaseType, string> = {
  vide: 'Location vide',
  meuble: 'Location meublée',
  mobilite: 'Bail mobilité',
  commercial: 'Bail commercial',
}

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  virement: 'Virement bancaire',
  cheque: 'Chèque',
  prelevement: 'Prélèvement',
  especes: 'Espèces',
}

export interface TenantInLease {
  id: string
  full_name: string
  email?: string
  phone?: string
  national_id?: string
}

export interface PropertyInLease {
  id: string
  name: string
  full_address: string
}

export interface Lease {
  id: string
  property_id: string
  tenant_id: string
  lease_type: LeaseType
  start_date: string
  end_date?: string
  notice_date?: string
  rent_amount: number
  charges_amount: number
  deposit_amount: number
  payment_day: number
  payment_method: PaymentMethod
  rent_call_rule: RentCallRule
  payment_frequency: PaymentFrequency
  apl_amount?: number
  apl_tiers_payant: boolean
  has_guarantor: boolean
  guarantor_name?: string
  guarantor_email?: string
  guarantor_phone?: string
  is_active: boolean
  total_monthly: number
  net_rent: number
  notes?: string
  tenant?: TenantInLease
  co_tenants?: TenantInLease[]
  all_tenant_names?: string
  parent_property?: PropertyInLease
  created_at: string
  updated_at: string
}

export interface LeaseListItem {
  id: string
  property_id: string
  tenant_id: string
  tenant_full_name: string
  property_name: string
  owner_name?: string | null
  lease_type: LeaseType
  start_date: string
  end_date?: string
  rent_amount: number
  charges_amount: number
  is_active: boolean
  apl_tiers_payant: boolean
}

export interface LeaseListResponse {
  items: LeaseListItem[]
  total: number
  skip: number
  limit: number
}
