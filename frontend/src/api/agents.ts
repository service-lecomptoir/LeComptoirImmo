import { apiClient } from './client'

/** Réponse à la génération d'un code de liaison Telegram. */
export interface TelegramLinkCode {
  code: string
  bot_username: string | null
  deep_link: string | null
  linked: boolean
  enabled: boolean
}

/** Statut de la liaison Telegram du gestionnaire. */
export interface TelegramStatus {
  linked: boolean
  bot_username: string | null
  enabled: boolean
}

export const agentsApi = {
  /** Statut courant de la liaison Telegram. */
  telegramStatus: () =>
    apiClient.get<TelegramStatus>('/agents/telegram/status'),
  /** Génère (ou régénère) un code de liaison à envoyer au bot. */
  generateLinkCode: () =>
    apiClient.post<TelegramLinkCode>('/agents/telegram/link-code'),
  /** Délie le compte Telegram. */
  unlink: () =>
    apiClient.post<{ linked: boolean }>('/agents/telegram/unlink'),
}
