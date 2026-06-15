import { apiClient } from './client'
import { BRAND } from '@/lib/brand'

export interface ScoreFactor {
  key: string
  label: string
  score: number
  weight: number
  detail: string
}

export interface ScoreStats {
  income: number | null
  monthly_total: number | null
  effort_rate: number | null
  on_time_rate: number | null
  payments_due: number
  overdue_count: number
  outstanding: number
  relationship_events_count: number
}

export interface ScoringRow {
  tenant_id: string
  tenant_name: string
  lease_id: string | null
  property_label: string | null
  owner_id: string | null
  owner_name: string
  has_active_lease: boolean
  score: number
  grade: 'A' | 'B' | 'C' | 'D' | 'E'
  strategy: string
  income: number | null
  effort_rate: number | null
  on_time_rate: number | null
  overdue_count: number
  outstanding: number
}

export interface RelationEvent {
  id: string
  date: string
  kind: string
  kind_label?: string
  polarity?: 'positif' | 'negatif' | 'neutre'
  note?: string | null
  author_name?: string | null
  created_at?: string
}

export interface ScoringDetail extends Omit<ScoringRow, 'income' | 'effort_rate' | 'on_time_rate' | 'overdue_count' | 'outstanding'> {
  tenant_phone?: string | null
  tenant_email?: string | null
  income_source?: string | null
  factors: ScoreFactor[]
  stats: ScoreStats
  relationship_events: RelationEvent[]
}

export interface EventKind {
  kind: string
  label: string
  polarity: 'positif' | 'negatif' | 'neutre'
  weight: number
}

export const scoringApi = {
  list: () => apiClient.get<{ total: number; items: ScoringRow[] }>('/scoring'),
  detail: (tenantId: string) => apiClient.get<ScoringDetail>(`/scoring/${tenantId}`),
  eventKinds: () => apiClient.get<EventKind[]>('/scoring/event-kinds'),
  // Événements de relation, portés par le contrat (lease)
  listEvents: (leaseId: string) => apiClient.get<RelationEvent[]>(`/leases/${leaseId}/relationship-events`),
  addEvent: (leaseId: string, data: { kind: string; note?: string; event_date?: string }) =>
    apiClient.post<RelationEvent[]>(`/leases/${leaseId}/relationship-events`, data),
  deleteEvent: (leaseId: string, eventId: string) =>
    apiClient.delete<RelationEvent[]>(`/leases/${leaseId}/relationship-events/${eventId}`),
}

export const GRADE_COLORS: Record<string, { color: string; bg: string }> = {
  A: { color: BRAND.teal, bg: '#D1FAE5' },
  B: { color: '#2563EB', bg: '#DBEAFE' },
  C: { color: '#D97706', bg: '#FEF3C7' },
  D: { color: '#EA580C', bg: '#FFEDD5' },
  E: { color: '#DC2626', bg: '#FEE2E2' },
}
