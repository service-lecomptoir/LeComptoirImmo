export type PaymentStatus = 'pending' | 'paid' | 'partial' | 'late' | 'cancelled'

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  pending: 'En attente',
  paid: 'Payé',
  partial: 'Partiel',
  late: 'En retard',
  cancelled: 'Annulé',
}

export const PAYMENT_STATUS_VARIANTS: Record<
  PaymentStatus,
  'green' | 'blue' | 'yellow' | 'red' | 'gray'
> = {
  pending: 'blue',
  paid: 'green',
  partial: 'yellow',
  late: 'red',
  cancelled: 'gray',
}

export interface TenantInPayment {
  id: string
  full_name: string
}

export interface Payment {
  id: string
  lease_id: string
  tenant_id: string
  period_year: number
  period_month: number
  period_label: string
  period_start?: string | null
  period_end?: string | null
  period_range_label?: string | null
  due_date: string
  amount_rent: number
  amount_charges: number
  amount_apl?: number
  amount_due: number
  amount_paid: number
  balance: number
  payment_date?: string
  payment_method?: string
  status: PaymentStatus
  settled_by_plan?: boolean
  notes?: string
  tenant?: TenantInPayment
  created_at: string
  updated_at: string
}

export interface PaymentListItem {
  id: string
  tenant_full_name: string
  property_name: string
  period_label: string
  period_start?: string | null
  period_end?: string | null
  period_range_label?: string | null
  period_year: number
  period_month: number
  due_date: string
  amount_apl?: number | null
  amount_due: number
  amount_paid: number
  balance: number
  credit_applied?: number
  amount_on_plan?: number
  payment_method?: string | null
  payment_date?: string | null
  status: PaymentStatus
  settled_by_plan?: boolean
  quittance_generated_at?: string | null
  quittance_sent_at?: string | null
  declared_at?: string | null
  declared_method?: string | null
  declared_amount?: number | null
}

export interface PaymentListResponse {
  items: PaymentListItem[]
  total: number
  skip: number
  limit: number
}

export interface MonthlyStats {
  period_label: string
  total_due: number
  total_paid: number
  total_balance: number
  paid_count: number
  pending_count: number
  partial_count: number
  late_count: number
}

export interface DashboardStats {
  monthly: MonthlyStats
  active_leases: number
  occupied_units: number
  total_units: number
  occupancy_rate: number
  total_tenants: number
}
