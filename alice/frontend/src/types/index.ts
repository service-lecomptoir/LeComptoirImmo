export interface Admin {
  id: string
  email: string
  full_name: string
  is_active: boolean
  created_at: string
}

export interface Plan {
  id: string
  name: string
  description: string | null
  property_limit: number | null
  monthly_price: number
  is_active: boolean
  created_at: string
  gestionnaire_count: number
}

export interface License {
  id: string
  gestionnaire_user_id: string
  plan_id: string | null
  property_limit_override: number | null
  monthly_price_override: number | null
  is_blocked: boolean
  access_until: string | null
  notes: string | null
  phone: string | null
  address: string | null
  created_at: string
  updated_at: string
}

export interface Gestionnaire {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
  license: License | null
  plan: Plan | null
  effective_property_limit: number | null
  property_count: number
}

export interface GestionnaireProperty {
  id: string
  name: string
  address: string | null
  zip_code: string | null
  city: string | null
}

export interface DashboardStats {
  total_gestionnaires: number
  gestionnaires_actifs: number
  gestionnaires_bloques: number
  total_biens: number
  mrr: number
  plans_distribution: Array<{ name: string; count: number; monthly_price: number }>
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
