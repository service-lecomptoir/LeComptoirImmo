import { apiClient } from './client'

export interface ProprietaireMessage {
  id: string
  proprietaire_id: string
  sender_id: string
  sender_name?: string
  content: string
  is_from_gestionnaire: boolean
  is_read: boolean
  created_at: string
}

export interface Conversation {
  proprietaire_id: string
  proprietaire_name: string
  last_message: string
  last_message_at: string
  unread_count: number
}

export const messagesApi = {
  list: (proprietaireId?: string) =>
    apiClient.get<{ messages?: ProprietaireMessage[]; conversations?: Conversation[] }>(
      '/proprietaire-messages',
      { params: proprietaireId ? { proprietaire_id: proprietaireId } : undefined }
    ),

  send: (content: string, proprietaireId?: string) =>
    apiClient.post<ProprietaireMessage>('/proprietaire-messages', {
      content,
      proprietaire_id: proprietaireId,
    }),

  unreadCount: () =>
    apiClient.get<{ unread: number }>('/proprietaire-messages/unread-count'),
}
