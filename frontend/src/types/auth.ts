export type Role = 'lecture' | 'comptable' | 'gestionnaire' | 'admin'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
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
