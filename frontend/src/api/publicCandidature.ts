import { apiClient } from './client'

export interface PublicCandidatureDoc {
  key: string
  label: string
  provided: boolean
  verified?: boolean
  filename?: string | null
}

export interface PublicCandidature {
  candidate_name: string
  property_name: string
  status: string
  documents: PublicCandidatureDoc[]
  all_provided: boolean
}

export interface PublicVisitSlot {
  id: string
  starts_at: string
  duration_min: number
  remaining: number
}

export interface PublicVisits {
  property_ref: string | null
  property_address: string | null
  candidate_name: string
  slots: PublicVisitSlot[]
  booked_slot_id: string | null
}

export const publicCandidatureApi = {
  get: (token: string) =>
    apiClient.get<PublicCandidature>(`/public/candidature/${token}`),
  getVisits: (token: string) =>
    apiClient.get<PublicVisits>(`/public/candidature/${token}/visits`),
  bookVisit: (token: string, slotId: string) =>
    apiClient.post<{ status: string; starts_at: string }>(
      `/public/candidature/${token}/visits/${slotId}/book`),
  upload: (token: string, key: string, file: File) => {
    const fd = new FormData()
    fd.append('key', key)
    fd.append('file', file)
    return apiClient.post<{ status: string; key: string; filename: string }>(
      `/public/candidature/${token}/upload`, fd,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },
  submit: (token: string) =>
    apiClient.post<{ status: string }>(`/public/candidature/${token}/submit`),
}
