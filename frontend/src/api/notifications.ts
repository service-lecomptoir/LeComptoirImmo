import { apiClient } from './client'
import type {
  Notification,
  NotificationListResponse,
  UnreadCountResponse,
} from '@/types/notification'

export interface BadgeCountResponse {
  total: number
  messages: number
  incidents: number
}

export const notificationsApi = {
  getUnreadCount: () =>
    apiClient.get<UnreadCountResponse>('/notifications/count'),

  getBadgeCount: () =>
    apiClient.get<BadgeCountResponse>('/notifications/badge'),

  list: (params?: { unread_only?: boolean; limit?: number }) =>
    apiClient.get<NotificationListResponse>('/notifications', { params }),

  markRead: (id: string) =>
    apiClient.post<Notification>(`/notifications/${id}/read`),

  markAllRead: () =>
    apiClient.post<{ marked_read: number }>('/notifications/read-all'),

  generateAlerts: () =>
    apiClient.post<{ late_payment_alerts: number; expiring_lease_alerts: number }>(
      '/notifications/generate-alerts'
    ),
}
