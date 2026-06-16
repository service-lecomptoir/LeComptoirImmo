export type Role = 'admin' | 'gestionnaire' | 'gestionnaire_proprio' | 'proprietaire' | 'locataire' | 'lecture' | 'comptable'

export interface User {
  id: string
  ref_code?: string | null
  email: string
  full_name: string
  role: Role
  is_active: boolean
  // Mot de passe temporaire (compte provisionné/réinitialisé) : tant que true,
  // l'utilisateur est forcé de définir un nouveau mot de passe à la connexion.
  must_change_password?: boolean
  phone?: string | null
  address?: string | null
  zip_code?: string | null
  city?: string | null
  country?: string | null
  owner_kind?: string | null
  owner_full_name?: string | null
  owner_company?: string | null
  owner_national_id?: string | null
  template_pinned_vars?: Record<string, string[]> | null
  logo_url?: string | null
  signature?: string | null
  signature_mode?: 'type' | 'draw' | null
  signature_text?: string | null
  signature_font?: string | null
  // Visibilité espace propriétaire : rubriques effectivement visibles (propriétaire),
  // et réglages bruts (gestionnaire).
  proprio_sections?: string[] | null
  proprio_visibility?: string[] | null
  proprio_visibility_default?: string[] | null
  last_login_at?: string | null
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
