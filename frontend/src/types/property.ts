export type PropertyType = 'immeuble' | 'maison' | 'appartement' | 'local_commercial' | 'autre'
export type UnitType = 'studio' | 'T1' | 'T2' | 'T3' | 'T4' | 'T5+' | 'maison' | 'local' | 'autre'

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
  owner_name: string | null
  owner_email: string | null
  owner_phone: string | null
  description: string | null
  notes: string | null
  year_built: number | null
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
  owner_name: string | null
  unit_count: number
  occupied_count: number
  created_at: string
}

export interface Unit {
  id: string
  property_id: string
  unit_ref: string
  unit_type: UnitType
  floor: number | null
  building: string | null
  area_sqm: number | null
  rooms: number | null
  bedrooms: number | null
  bathrooms: number | null
  base_rent: number
  charges_amount: number
  deposit_months: number
  deposit_amount: number
  total_monthly: number
  is_occupied: boolean
  is_available: boolean
  notes: string | null
  created_at: string
  updated_at: string
}
