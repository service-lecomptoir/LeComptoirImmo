import { apiClient } from './client'

export interface Ticket {
  id: string
  title: string
  description: string
  category: 'incident' | 'question' | 'demande' | 'autre'
  status: 'open' | 'in_progress' | 'resolved' | 'closed'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  tenant_id: string
  tenant_name?: string
  lease_id?: string
  assigned_to_id?: string
  assigned_to_name?: string
  closed_at?: string
  messages?: TicketMessage[]
  message_count?: number
  created_at: string
  updated_at: string
}

export interface TicketMessage {
  id: string
  ticket_id: string
  author_id: string
  author_name?: string
  author_role?: string
  content: string
  is_internal: boolean
  created_at: string
}

export const ticketsApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) =>
    apiClient.get<{ total: number; items: Ticket[] }>('/tickets', { params }),

  mine: () =>
    apiClient.get<Ticket[]>('/tickets/mine'),

  get: (id: string) =>
    apiClient.get<Ticket>(`/tickets/${id}`),

  create: (data: { title: string; description: string; category: string; priority: string }) =>
    apiClient.post<{ id: string; status: string }>('/tickets', data),

  update: (id: string, data: Partial<Pick<Ticket, 'title' | 'description' | 'category' | 'priority' | 'status' | 'assigned_to_id'>>) =>
    apiClient.patch<Ticket>(`/tickets/${id}`, data),

  addMessage: (id: string, content: string, is_internal = false) =>
    apiClient.post<TicketMessage>(`/tickets/${id}/messages`, { content, is_internal }),

  stats: () =>
    apiClient.get<{ open: number }>('/tickets/stats'),

  proprietaire: (params?: { status?: string }) =>
    apiClient.get<{ total: number; items: Ticket[] }>('/tickets/proprietaire', { params }),
}
