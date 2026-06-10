export type Role = 'admin' | 'gestionnaire' | 'gestionnaire_proprio' | 'proprietaire' | 'locataire' | 'lecture' | 'comptable'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  phone?: string | null
  address?: string | null
  zip_code?: string | null
  city?: string | null
  country?: string | null
  owner_full_name?: string | null
  owner_company?: string | null
  owner_national_id?: string | null
  template_pinned_vars?: Record<string, string[]> | null
  logo_url?: string | null
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}
