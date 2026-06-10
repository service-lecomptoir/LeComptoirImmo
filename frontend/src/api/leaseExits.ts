import { apiClient } from './client'

export type ExitStatus = 'preavis' | 'etat_des_lieux' | 'decompte' | 'cloture'

export interface ExitInspection {
  id: string
  inspection_type: string
  inspection_date: string
  inspector_name?: string | null
  overall_condition?: string | null
  notes?: string | null
}

export interface Deduction {
  label: string
  amount: number
}

export interface LeaseExit {
  id: string
  lease_id: string
  status: ExitStatus
  tenant_name?: string | null
  property_id: string
  property_name?: string | null
  lease_is_active: boolean
  notice_received_at?: string | null
  departure_date?: string | null
  entry_inspection?: ExitInspection | null
  exit_inspection?: ExitInspection | null
  deposit_amount: number
  deductions: Deduction[]
  total_deductions: number
  deposit_to_return: number
  comments?: string | null
  closed_at?: string | null
  created_at: string
  lease_inspections: ExitInspection[]
}

export interface ExitUpdate {
  status?: 'preavis' | 'etat_des_lieux' | 'decompte'
  notice_received_at?: string | null
  departure_date?: string | null
  entry_inspection_id?: string | null
  exit_inspection_id?: string | null
  deductions?: Deduction[]
  comments?: string | null
}

export const leaseExitsApi = {
  list: (params?: { status?: string }) =>
    apiClient.get<LeaseExit[]>('/lease-exits', { params }),
  byLease: (leaseId: string) =>
    apiClient.get<LeaseExit | null>(`/lease-exits/by-lease/${leaseId}`),
  create: (data: { lease_id: string; notice_received_at?: string; departure_date?: string }) =>
    apiClient.post<LeaseExit>('/lease-exits', data),
  update: (id: string, data: ExitUpdate) =>
    apiClient.patch<LeaseExit>(`/lease-exits/${id}`, data),
  close: (id: string) => apiClient.post<LeaseExit>(`/lease-exits/${id}/close`),
  remove: (id: string) => apiClient.delete(`/lease-exits/${id}`),
}
