export type NotificationType =
  | 'loyer_retard'
  | 'bail_expire_soon'
  | 'bail_expire'
  | 'paiement_recu'
  | 'systeme'

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  loyer_retard: 'Loyer en retard',
  bail_expire_soon: 'Bail expirant bientôt',
  bail_expire: 'Bail expiré',
  paiement_recu: 'Paiement reçu',
  systeme: 'Système',
}

export const NOTIFICATION_PRIORITY_VARIANTS: Record<
  NotificationPriority,
  'red' | 'yellow' | 'blue' | 'gray'
> = {
  urgent: 'red',
  high: 'red',
  normal: 'blue',
  low: 'gray',
}

export interface Notification {
  id: string
  notification_type: NotificationType
  priority: NotificationPriority
  title: string
  message: string
  entity_type?: string
  entity_id?: string
  is_read: boolean
  read_at?: string
  user_id?: string
  created_at: string
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  unread_count: number
}

export interface UnreadCountResponse {
  count: number
}
