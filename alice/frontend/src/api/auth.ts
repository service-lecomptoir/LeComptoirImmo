import { apiClient } from './client'
import type { Admin, TokenResponse } from '@/types'

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/login', { email, password }),

  me: () =>
    apiClient.get<Admin>('/auth/me'),
}
