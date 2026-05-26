export type InspectionType = 'entree' | 'sortie' | 'contradictoire' | 'periodique'
export type OverallCondition = 'tres_bon' | 'bon' | 'moyen' | 'mauvais'

export const INSPECTION_TYPE_LABELS: Record<InspectionType, string> = {
  entree: 'État des lieux d\'entrée',
  sortie: 'État des lieux de sortie',
  contradictoire: 'Contradictoire',
  periodique: 'Visite périodique',
}

export const CONDITION_LABELS: Record<OverallCondition, string> = {
  tres_bon: 'Très bon',
  bon: 'Bon',
  moyen: 'Moyen',
  mauvais: 'Mauvais',
}

export const CONDITION_VARIANTS: Record<OverallCondition, 'green' | 'blue' | 'yellow' | 'red'> = {
  tres_bon: 'green',
  bon: 'blue',
  moyen: 'yellow',
  mauvais: 'red',
}

export interface Inspection {
  id: string
  lease_id?: string
  property_id?: string
  inspection_type: InspectionType
  inspection_date: string
  inspector_name?: string
  tenant_present: boolean
  overall_condition?: OverallCondition
  notes?: string
  rooms_data?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface InspectionListResponse {
  items: Inspection[]
  total: number
  skip: number
  limit: number
}
