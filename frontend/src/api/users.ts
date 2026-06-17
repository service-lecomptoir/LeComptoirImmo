import { apiClient } from './client'
import type { User } from '@/types/auth'

interface CreateUserPayload {
  full_name: string
  email: string
  /** Facultatif : si absent, le serveur génère un mot de passe et l'envoie par e-mail. */
  password?: string
  role: string
  phone?: string
}

export type CreatedUser = User & { credentials_email_sent?: boolean }

export const usersApi = {
  /** Liste tous les utilisateurs (admin) ou propriétaires/locataires (gestionnaire).
   *  `unlinked_tenant` exclut les comptes déjà rattachés à une fiche locataire. */
  list: (params?: { role?: string; unlinked_tenant?: boolean; unlinked_owner?: boolean; owner_id?: string }) =>
    apiClient.get<User[]>('/users', { params }),

  /** Crée un compte utilisateur */
  create: (data: CreateUserPayload) =>
    apiClient.post<CreatedUser>('/users', data),

  /** Retourne le profil de l'utilisateur connecté */
  me: () =>
    apiClient.get<User>('/users/me'),

  /** Coordonnées de l'agence de rattachement (locataire / propriétaire). null si aucune. */
  myManager: () =>
    apiClient.get<ManagerContact | null>('/users/me/manager'),

  /** Domaines e-mail autorisés du compte connecté */
  listEmailDomains: () =>
    apiClient.get<EmailDomain[]>('/users/me/email-domains'),
  addEmailDomain: (domain: string) =>
    apiClient.post<EmailDomain>('/users/me/email-domains', { domain }),
  removeEmailDomain: (id: string) =>
    apiClient.delete(`/users/me/email-domains/${id}`),
}

export interface EmailDomain {
  id: string
  domain: string
}

export interface ManagerContact {
  full_name: string
  email: string
  phone: string | null
  address: string | null
}
