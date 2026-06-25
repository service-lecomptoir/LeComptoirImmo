export type PropertyType = 'appartement' | 'maison' | 'local_commercial' | 'autre'

export const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  appartement: 'Appartement',
  maison: 'Maison',
  local_commercial: 'Local commercial',
  autre: 'Autre',
}

export const TYPOLOGY_OPTIONS = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10'] as const

// Modes de chauffage — couvre les énergies courantes du parc français.
// (valeurs ≤ 30 car. : contrainte colonne heating_type VARCHAR(30))
export const HEATING_OPTIONS: { value: string; label: string }[] = [
  { value: 'individuel_gaz', label: 'Individuel : gaz' },
  { value: 'individuel_elec', label: 'Individuel : électrique' },
  { value: 'pompe_chaleur', label: 'Pompe à chaleur' },
  { value: 'fioul', label: 'Fioul' },
  { value: 'bois_granules', label: 'Bois / granulés (pellets)' },
  { value: 'collectif', label: 'Collectif (immeuble)' },
  { value: 'reseau_urbain', label: 'Réseau de chaleur urbain' },
  { value: 'autre', label: 'Autre' },
]

// Classes DPE A→G + « NS » (non soumis / vierge). Valeurs ≤ 2 car. (colonne VARCHAR(2)).
export const ENERGY_CLASSES: { value: string; label: string }[] = [
  { value: 'A', label: 'A : très performant' },
  { value: 'B', label: 'B' },
  { value: 'C', label: 'C' },
  { value: 'D', label: 'D' },
  { value: 'E', label: 'E' },
  { value: 'F', label: 'F' },
  { value: 'G', label: 'G : passoire thermique' },
  { value: 'NS', label: 'Non soumis / vierge' },
]

export type AmenityKey =
  | 'furnished' | 'kitchen_equipped' | 'has_elevator' | 'has_balcony'
  | 'has_terrace' | 'has_garden' | 'has_parking' | 'has_cellar' | 'has_fiber'
  | 'has_air_conditioning'

// Équipements / extérieurs — clé technique → libellé affiché
export const AMENITIES: { key: AmenityKey; label: string }[] = [
  { key: 'furnished', label: 'Meublé' },
  { key: 'kitchen_equipped', label: 'Cuisine équipée' },
  { key: 'has_fiber', label: 'Fibre internet' },
  { key: 'has_air_conditioning', label: 'Climatisation' },
  { key: 'has_elevator', label: 'Ascenseur' },
  { key: 'has_balcony', label: 'Balcon' },
  { key: 'has_terrace', label: 'Terrasse' },
  { key: 'has_garden', label: 'Jardin' },
  { key: 'has_parking', label: 'Parking / garage' },
  { key: 'has_cellar', label: 'Cave' },
]

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
  owner_id: string | null
  owner_user_id: string | null
  owner_name: string | null
  account_name?: string | null
  owner_national_id?: string | null
  owner_email: string | null
  owner_phone: string | null
  description: string | null
  notes: string | null
  year_built: number | null
  // ── Acquisition (achat ou construction) ────────────────────────────────────
  acquisition_date: string | null
  acquisition_value: number | null
  // ── Caractéristiques du bien ───────────────────────────────────────────────
  typology: string | null          // T1 … T10
  floor: number | null
  area_sqm: number | null
  bathrooms: number | null         // salles d'eau / de bain
  heating_type: string | null
  energy_class: string | null
  // ── Équipements & extérieurs ───────────────────────────────────────────────
  furnished: boolean
  kitchen_equipped: boolean
  has_elevator: boolean
  has_balcony: boolean
  has_terrace: boolean
  has_garden: boolean
  has_parking: boolean
  has_cellar: boolean
  has_fiber: boolean
  has_air_conditioning: boolean
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
  owner_id: string | null
  owner_user_id: string | null
  owner_name: string | null
  account_name?: string | null
  typology: string | null
  area_sqm: number | null
  is_occupied: boolean
  unit_count: number
  occupied_count: number
  created_at: string
}
