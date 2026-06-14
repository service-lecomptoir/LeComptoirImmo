import { apiClient } from './client'
import type { User } from '@/types/auth'

interface CreateUserPayload {
  full_name: string
  email: string
  password: string
  role: string
  phone?: string
}

export const usersApi = {
  /** Liste tous les utilisateurs (admin) ou propriétaires/locataires (gestionnaire).
   *  `unlinked_tenant` exclut les comptes déjà rattachés à une fiche locataire. */
  list: (params?: { role?: string; unlinked_tenant?: boolean; unlinked_owner?: boolean; owner_id?: string }) =>
    apiClient.get<User[]>('/users', { params }),

  /** Crée un compte utilisateur */
  create: (data: CreateUserPayload) =>
    apiClient.post<User>('/users', data),

  /** Retourne le profil de l'utilisateur connecté */
  me: () =>
    apiClient.get<User>('/users/me'),

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
