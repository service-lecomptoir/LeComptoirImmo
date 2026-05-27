export type Role = 'admin' | 'gestionnaire' | 'gestionnaire_proprio' | 'proprietaire' | 'locataire' | 'lecture' | 'comptable'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  phone?: string | null
  address?: string | null
  iban?: string | null
  bic?: string | null
  bank_holder?: string | null
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
