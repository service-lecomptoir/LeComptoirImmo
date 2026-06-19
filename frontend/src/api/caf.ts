import { apiClient } from './client'

export type CafDocType = 'attestation' | 'tiers_payant'

export interface CafTemplateInfo {
  doc_type: CafDocType | null
  has_template: boolean
  original_filename: string | null
  field_map: Record<string, string>
  fields: string[]
  sign_page: number
  sign_x_mm: number
  sign_y_mm: number
  sign_w_mm: number
}

export interface CafDataKey { key: string; label: string }

export const cafApi = {
  dataKeys: () => apiClient.get<CafDataKey[]>('/caf/data-keys'),
  templates: () => apiClient.get<Record<CafDocType, CafTemplateInfo>>('/caf/templates'),
  upload: (docType: CafDocType, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiClient.post<CafTemplateInfo>(`/caf/templates/${docType}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  saveMapping: (docType: CafDocType, data: {
    field_map: Record<string, string>
    sign_page?: number; sign_x_mm?: number; sign_y_mm?: number; sign_w_mm?: number
  }) => apiClient.put<CafTemplateInfo>(`/caf/templates/${docType}`, data),
  remove: (docType: CafDocType) => apiClient.delete(`/caf/templates/${docType}`),
  pdfUrl: (leaseId: string, docType: CafDocType) => `/caf/${leaseId}/${docType}/pdf`,
  openPdf: (leaseId: string, docType: CafDocType) =>
    apiClient.get(`/caf/${leaseId}/${docType}/pdf`, { responseType: 'blob' }),
  email: (leaseId: string, docType: CafDocType) =>
    apiClient.post<{ email_sent: boolean }>(`/caf/${leaseId}/${docType}/email`),
  deposit: (leaseId: string, docType: CafDocType) =>
    apiClient.post<{ deposited: boolean }>(`/caf/${leaseId}/${docType}/deposit`),
}
