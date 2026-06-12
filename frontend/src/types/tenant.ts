export type Civility = 'M' | 'Mme' | 'Autre'

export interface Tenant {
  id: string
  civility: Civility | null
  first_name: string
  last_name: string
  company_name: string | null
  siret: string | null
  full_name: string
  birth_date: string | null
  birth_place: string | null
  national_id: string | null
  email: string | null
  phone: string | null
  phone2: string | null
  employer: string | null
  employer_phone: string | null
  monthly_income: number | null
  income_source: string | null
  notes: string | null
  user_id: string | null
  created_at: string
  updated_at: string
}

export interface TenantListItem {
  id: string
  full_name: string
  civility: Civility | null
  first_name: string
  last_name: string
  company_name: string | null
  email: string | null
  phone: string | null
  user_id: string | null
  created_at: string
}

export interface TenantCreate {
  civility?: Civility
  first_name?: string
  last_name?: string
  company_name?: string
  siret?: string
  birth_date?: string
  birth_place?: string
  national_id?: string
  email?: string
  phone?: string
  phone2?: string
  employer?: string
  employer_phone?: string
  monthly_income?: number
  income_source?: string
  notes?: string
  user_id?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}
