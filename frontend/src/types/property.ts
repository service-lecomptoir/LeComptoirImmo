export type PropertyType = 'appartement' | 'maison' | 'local_commercial' | 'autre'

export const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  appartement: 'Appartement',
  maison: 'Maison',
  local_commercial: 'Local commercial',
  autre: 'Autre',
}

export interface Property {
  id: string
  name: string
  reference: string | null
  address: string
  address2: string | null
  zip_code: string
  city: string
  country: string
  property_type: PropertyType
  full_address: string
  owner_user_id: string | null
  owner_name: string | null
  owner_email: string | null
  owner_phone: string | null
  description: string | null
  notes: string | null
  year_built: number | null
  // ── Caractéristiques du bien (fusionnées depuis le logement) ───────────────
  floor: number | null
  area_sqm: number | null
  rooms: number | null
  bedrooms: number | null
  bathrooms: number | null
  base_rent: number
  charges_amount: number
  deposit_months: number
  is_occupied: boolean
  is_available: boolean
  unit_count: number
  occupied_count: number
  created_at: string
  updated_at: string
}

export interface PropertyListItem {
  id: string
  name: string
  city: string
  property_type: PropertyType
  full_address: string
  owner_user_id: string | null
  owner_name: string | null
  area_sqm: number | null
  base_rent: number
  is_occupied: boolean
  unit_count: number
  occupied_count: number
  created_at: string
}
