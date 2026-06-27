import { apiClient } from './client'

/** Une ligne du journal d'audit de l'agence (acteurs : gestionnaire, comptable,
 *  propriétaires, locataires liés). Voir backend app/api/v1/audit.py. */
export interface AuditLog {
  id: string
  created_at: string
  user_id: string | null
  user_email: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  details: unknown
  ip_address: string | null
}

export interface AuditQuery {
  action?: string
  entity_type?: string
  user_email?: string
  limit?: number
  skip?: number
}

export const auditApi = {
  list: (params?: AuditQuery) => apiClient.get<AuditLog[]>('/audit', { params }),
}
