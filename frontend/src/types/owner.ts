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
  phone2: string | null
  address: string | null
  iban: string | null
  bic: string | null
  bank_holder: string | null
  notes: string | null
  user_id: string | null
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
  phone2?: string
  address?: string
  iban?: string
  bic?: string
  bank_holder?: string
  notes?: string
  user_id?: string
}

export type { PaginatedResponse }
