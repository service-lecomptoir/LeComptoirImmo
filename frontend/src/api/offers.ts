import { apiClient } from './client'

export interface Offer {
  id: string
  title: string
  description?: string
  price?: number | null
  category: string
  contact_info?: string
  image_url?: string | null
  is_active: boolean
  gestionnaire_id?: string
  created_at: string
}

export interface OfferCreate {
  title: string
  description?: string
  price?: number | null
  category: string
  contact_info?: string
  is_active?: boolean
}

export const OFFER_CATEGORIES = [
  { value: 'service',   label: 'Service' },
  { value: 'article',   label: 'Article' },
  { value: 'promotion', label: 'Promotion' },
  { value: 'autre',     label: 'Autre' },
]

export const offersApi = {
  list: () => apiClient.get<Offer[]>('/offers'),
  listForTenant: () => apiClient.get<Offer[]>('/offers/me'),
  create: (data: OfferCreate) => apiClient.post<Offer>('/offers', data),
  update: (id: string, data: Partial<OfferCreate>) => apiClient.patch<Offer>(`/offers/${id}`, data),
  uploadImage: (id: string, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiClient.post<Offer>(`/offers/${id}/upload-image`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (id: string) => apiClient.delete(`/offers/${id}`),
}
