import { apiClient } from './client'

export interface PublicCandidatureDoc {
  key: string
  label: string
  provided: boolean
  filename?: string | null
}

export interface PublicCandidature {
  candidate_name: string
  property_name: string
  status: string
  documents: PublicCandidatureDoc[]
  all_provided: boolean
}

export const publicCandidatureApi = {
  get: (token: string) =>
    apiClient.get<PublicCandidature>(`/public/candidature/${token}`),
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
