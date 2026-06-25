import type { Civility, PaginatedResponse } from './tenant'

export interface Owner {
  id: string
  civility: Civility | null
  first_name: string | null
  last_name: string
  company_name: string | null
  full_name: string
  national_id: string | null
  email: string | null
  phone: string | null
  address: string | null
  zip_code: string | null
  city: string | null
  country: string | null
  iban: string | null
  bic: string | null
  bank_holder: string | null
  mgmt_fee_rate: number | null
  notes: string | null
  user_id: string | null
  user_is_proprietaire?: boolean
  created_at: string
  updated_at: string
}

export interface OwnerListItem {
  id: string
  full_name: string
  civility: Civility | null
  first_name: string | null
  last_name: string
  company_name: string | null
  email: string | null
  phone: string | null
  user_id: string | null
  created_at: string
}

export interface OwnerCreate {
  civility?: Civility
  first_name?: string
  last_name: string
  company_name?: string
  national_id?: string
  email?: string
  phone?: string
  address?: string
  zip_code?: string
  city?: string
  country?: string
  iban?: string
  bic?: string
  bank_holder?: string
  mgmt_fee_rate?: number | null
  notes?: string
  user_id?: string
}

export type { PaginatedResponse }
