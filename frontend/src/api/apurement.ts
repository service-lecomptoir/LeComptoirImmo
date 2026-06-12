import { apiClient } from './client'
import { downloadBlob } from '@/utils/download'

export interface PlanInstallment {
  seq: number
  due_date: string
  amount: number
  paid: boolean
  paid_date: string | null
  declared?: boolean
  declared_date?: string | null
}

export interface ApurementPlan {
  id: string
  lease_id: string
  tenant_id: string
  tenant_name: string | null
  property_name: string | null
  total_amount: number
  installments: PlanInstallment[]
  status: string
  label: string | null
  created_at: string
  paid_total: number
  remaining: number
  paid_count: number
  count: number
  overdue: boolean
}

export const apurementApi = {
  create: (payment_id: string, installments: number, first_date: string) =>
    apiClient.post<ApurementPlan>('/apurement-plans', { payment_id, installments, first_date }),
  listForTenant: (tenant_id: string) =>
    apiClient.get<ApurementPlan[]>('/apurement-plans', { params: { tenant_id } }),
  mine: () => apiClient.get<ApurementPlan[]>('/apurement-plans/mine'),
  listActive: () => apiClient.get<ApurementPlan[]>('/apurement-plans/active'),
  declareInstallment: (planId: string, seq: number) =>
    apiClient.post<ApurementPlan>(`/apurement-plans/${planId}/installments/${seq}/declare`),
  markInstallment: (planId: string, seq: number, paid: boolean, paid_date?: string | null) =>
    apiClient.patch<ApurementPlan>(`/apurement-plans/${planId}/installments/${seq}`, { paid, paid_date: paid_date ?? null }),
  remove: (planId: string) => apiClient.delete(`/apurement-plans/${planId}`),
  downloadPdf: async (planId: string, filename: string) => {
    const res = await apiClient.get(`/apurement-plans/${planId}/pdf`, { responseType: 'blob' })
    downloadBlob(res.data, filename)
  },
}
