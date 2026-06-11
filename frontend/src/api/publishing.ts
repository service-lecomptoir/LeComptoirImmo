import { apiClient } from './client'

export type PlatformKind = 'reseau' | 'site' | 'email' | 'lien' | 'autre'
export type ListingStatus = 'draft' | 'scheduled' | 'published' | 'unpublished'

export interface PublishPlatform {
  id: string
  name: string
  kind: PlatformKind
  target?: string | null
  is_active: boolean
}

export interface ListingPhoto {
  id: string
  url: string
  label?: string | null
}

export interface Listing {
  id: string
  property_id: string
  title?: string | null
  description?: string | null
  price?: number | null
  photo_ids: string[]
  platform_ids: string[]
  status: ListingStatus
  public_token?: string | null
  public_path?: string | null
  scheduled_at?: string | null
  published_at?: string | null
  views_count: number
  last_viewed_at?: string | null
  available_photos: ListingPhoto[]
}

/** Statut + performances d'une annonce (vue d'ensemble), indexé par bien. */
export interface ListingOverview {
  property_id: string
  status: ListingStatus
  public_path?: string | null
  scheduled_at?: string | null
  published_at?: string | null
  views_count: number
  last_viewed_at?: string | null
}

export interface ListingSave {
  title?: string | null
  description?: string | null
  price?: number | null
  photo_ids?: string[]
  platform_ids?: string[]
}

export const publishingApi = {
  // Plateformes de diffusion (cibles de partage définies au préalable)
  listPlatforms: () => apiClient.get<PublishPlatform[]>('/publishing/platforms'),
  createPlatform: (d: Omit<PublishPlatform, 'id'>) =>
    apiClient.post<PublishPlatform>('/publishing/platforms', d),
  updatePlatform: (id: string, d: Omit<PublishPlatform, 'id'>) =>
    apiClient.put<PublishPlatform>(`/publishing/platforms/${id}`, d),
  deletePlatform: (id: string) => apiClient.delete(`/publishing/platforms/${id}`),

  // Vue d'ensemble (statut + vues par bien)
  listListings: () => apiClient.get<ListingOverview[]>('/publishing/listings'),

  // Annonce d'un bien
  getListing: (propertyId: string) =>
    apiClient.get<Listing>(`/publishing/properties/${propertyId}/listing`),
  saveListing: (propertyId: string, d: ListingSave) =>
    apiClient.put<Listing>(`/publishing/properties/${propertyId}/listing`, d),
  publish: (propertyId: string) =>
    apiClient.post<Listing>(`/publishing/properties/${propertyId}/listing/publish`),
  schedule: (propertyId: string, scheduled_at: string) =>
    apiClient.post<Listing>(`/publishing/properties/${propertyId}/listing/schedule`, { scheduled_at }),
  unpublish: (propertyId: string) =>
    apiClient.post<Listing>(`/publishing/properties/${propertyId}/listing/unpublish`),
  deletePhoto: (propertyId: string, documentId: string) =>
    apiClient.delete(`/publishing/properties/${propertyId}/photos/${documentId}`),
  generate: (propertyId: string) =>
    apiClient.post<{ title: string; description: string; source: string }>(
      `/publishing/properties/${propertyId}/listing/generate`,
    ),
}

/** Upload d'une photo rattachée au bien (document image), réutilisable dans l'annonce. */
export async function uploadPropertyPhoto(propertyId: string, file: File, label?: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('entity_type', 'property')
  form.append('entity_id', propertyId)
  form.append('document_type', 'photo')
  if (label) form.append('label', label)
  const token = localStorage.getItem('access_token')
  const base = import.meta.env.VITE_API_URL || ''
  const r = await fetch(`${base}/api/v1/documents/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error(typeof err?.detail === 'string' ? err.detail : "Échec de l'envoi de la photo")
  }
  return r.json()
}
