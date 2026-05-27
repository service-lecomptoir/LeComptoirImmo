import { apiClient } from './client'
import type { LoginRequest, TokenResponse, User } from '@/types/auth'

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', data),

  refresh: (refresh_token: string) =>
    apiClient.post<{ access_token: string }>('/auth/refresh', { refresh_token }),

  me: () =>
    apiClient.get<User>('/auth/me'),

  updateProfile: (data: {
    full_name?: string
    phone?: string | null
    address?: string | null
    iban?: string | null
    bic?: string | null
    bank_holder?: string | null
  }) =>
    apiClient.patch<User>('/auth/me', data),
}
