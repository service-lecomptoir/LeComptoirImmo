import { apiClient } from './client'
import { downloadBlob } from '@/utils/download'

export interface CoproListItem {
  id: string
  ref_code?: string | null
  name: string
  city?: string | null
  immatriculation?: string | null
  lot_count: number
  created_at: string
}

export interface RepartitionKey {
  id: string
  name: string
  total_tantiemes: number
  is_general: boolean
  position: number
  assigned_tantiemes: number
  balanced: boolean
}

export interface CoproLot {
  id: string
  numero: string
  lot_type?: string | null
  floor?: string | null
  description?: string | null
  owner_id?: string | null
  owner_name?: string | null
  property_id?: string | null
  tantiemes: Record<string, number> // key_id -> valeur
}

export interface CoproDetail {
  id: string
  ref_code?: string | null
  name: string
  immatriculation?: string | null
  address?: string | null
  zip_code?: string | null
  city?: string | null
  country?: string | null
  construction_year?: number | null
  notes?: string | null
  keys: RepartitionKey[]
  lots: CoproLot[]
  created_at: string
  updated_at: string
}

export interface CoproInput {
  name: string
  immatriculation?: string | null
  address?: string | null
  zip_code?: string | null
  city?: string | null
  country?: string | null
  construction_year?: number | null
  notes?: string | null
}

export interface KeyInput {
  name: string
  total_tantiemes: number
  is_general?: boolean
  position?: number
}

export interface LotInput {
  numero: string
  lot_type?: string | null
  floor?: string | null
  description?: string | null
  owner_id?: string | null
  property_id?: string | null
  tantiemes: { key_id: string; tantiemes: number }[]
}

export type Periodicity = 'mensuel' | 'trimestriel' | 'semestriel' | 'annuel'

export interface BudgetLine {
  id?: string
  key_id: string
  key_name?: string | null
  label: string
  amount: number
}
export interface Budget {
  id: string
  copropriete_id: string
  year: number
  periodicity: Periodicity
  label?: string | null
  total: number
  nb_periods: number
  lines: BudgetLine[]
}
export interface BudgetInput {
  year: number
  periodicity: Periodicity
  label?: string | null
  lines: { key_id: string; label: string; amount: number }[]
}
export interface CallItem {
  id: string
  lot_id?: string | null
  lot_numero?: string | null
  owner_id?: string | null
  owner_name?: string | null
  amount_due: number
  amount_paid: number
  status: string
}
export interface FundCall {
  id: string
  period_index: number
  period_label: string
  due_date?: string | null
  total_due: number
  total_paid: number
  items: CallItem[]
}
export interface CoproAccount {
  owner_id?: string | null
  owner_name?: string | null
  total_due: number
  total_paid: number
  balance: number
}
export interface CoproExpense {
  id: string
  year: number
  key_id: string
  key_name?: string | null
  label: string
  amount: number
  expense_date?: string | null
  supplier?: string | null
}
export interface ExpenseInput {
  year: number
  key_id: string
  label: string
  amount: number
  expense_date?: string | null
  supplier?: string | null
}
export interface RegularizationRow {
  owner_id?: string | null
  owner_name?: string | null
  appele: number
  reel: number
  solde: number
}
export interface RegularizationResult {
  year: number
  budget_total: number
  expenses_total: number
  appele_total: number
  rows: RegularizationRow[]
}

export const coproApi = {
  list: () => apiClient.get<CoproListItem[]>('/coproprietes'),
  get: (id: string) => apiClient.get<CoproDetail>(`/coproprietes/${id}`),
  create: (data: CoproInput) => apiClient.post<CoproDetail>('/coproprietes', data),
  update: (id: string, data: Partial<CoproInput>) => apiClient.put<CoproDetail>(`/coproprietes/${id}`, data),
  delete: (id: string) => apiClient.delete(`/coproprietes/${id}`),

  addKey: (id: string, data: KeyInput) => apiClient.post<RepartitionKey>(`/coproprietes/${id}/keys`, data),
  updateKey: (id: string, keyId: string, data: Partial<KeyInput>) => apiClient.put<RepartitionKey>(`/coproprietes/${id}/keys/${keyId}`, data),
  deleteKey: (id: string, keyId: string) => apiClient.delete(`/coproprietes/${id}/keys/${keyId}`),

  createLot: (id: string, data: LotInput) => apiClient.post<CoproLot>(`/coproprietes/${id}/lots`, data),
  updateLot: (id: string, lotId: string, data: Partial<LotInput>) => apiClient.put<CoproLot>(`/coproprietes/${id}/lots/${lotId}`, data),
  deleteLot: (id: string, lotId: string) => apiClient.delete(`/coproprietes/${id}/lots/${lotId}`),

  // ── Comptabilité copro ──
  getBudget: (id: string, year: number) => apiClient.get<Budget | null>(`/coproprietes/${id}/budget`, { params: { year } }),
  createBudget: (id: string, data: BudgetInput) => apiClient.post<Budget>(`/coproprietes/${id}/budgets`, data),
  updateBudget: (id: string, budgetId: string, data: Partial<BudgetInput>) => apiClient.put<Budget>(`/coproprietes/${id}/budgets/${budgetId}`, data),
  deleteBudget: (id: string, budgetId: string) => apiClient.delete(`/coproprietes/${id}/budgets/${budgetId}`),

  listCalls: (id: string, budgetId: string) => apiClient.get<FundCall[]>(`/coproprietes/${id}/budgets/${budgetId}/calls`),
  generateCall: (id: string, budgetId: string, period_index: number, due_date?: string | null) =>
    apiClient.post<FundCall>(`/coproprietes/${id}/budgets/${budgetId}/calls`, { period_index, due_date: due_date || null }),
  deleteCall: (id: string, callId: string) => apiClient.delete(`/coproprietes/${id}/calls/${callId}`),

  recordPayment: (id: string, itemId: string, data: { amount: number; payment_date: string; method?: string | null; note?: string | null }) =>
    apiClient.post(`/coproprietes/${id}/call-items/${itemId}/payments`, data),

  accounts: (id: string, year: number) => apiClient.get<CoproAccount[]>(`/coproprietes/${id}/accounts`, { params: { year } }),

  appelPdf: async (id: string, itemId: string, filename: string) => {
    const r = await apiClient.get(`/coproprietes/${id}/call-items/${itemId}/appel/pdf`, { responseType: 'blob' })
    downloadBlob(r.data, filename)
  },

  // ── Régularisation ──
  listExpenses: (id: string, year: number) => apiClient.get<CoproExpense[]>(`/coproprietes/${id}/expenses`, { params: { year } }),
  createExpense: (id: string, data: ExpenseInput) => apiClient.post<CoproExpense>(`/coproprietes/${id}/expenses`, data),
  updateExpense: (id: string, expenseId: string, data: Partial<ExpenseInput>) => apiClient.put<CoproExpense>(`/coproprietes/${id}/expenses/${expenseId}`, data),
  deleteExpense: (id: string, expenseId: string) => apiClient.delete(`/coproprietes/${id}/expenses/${expenseId}`),

  regularization: (id: string, year: number) => apiClient.get<RegularizationResult>(`/coproprietes/${id}/regularization`, { params: { year } }),
  regulPdf: async (id: string, ownerId: string, year: number, filename: string) => {
    const r = await apiClient.get(`/coproprietes/${id}/regularization/${ownerId}/pdf`, { params: { year }, responseType: 'blob' })
    downloadBlob(r.data, filename)
  },
}
