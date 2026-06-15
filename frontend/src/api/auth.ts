import { apiClient } from './client'
import type { LoginRequest, TokenResponse, User } from '@/types/auth'

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', data),

  refresh: (refresh_token: string) =>
    apiClient.post<{ access_token: string }>('/auth/refresh', { refresh_token }),

  forgotPassword: (email: string) =>
    apiClient.post<{ detail: string }>('/auth/forgot-password', { email }),

  me: () =>
    apiClient.get<User>('/auth/me'),

  updateProfile: (data: {
    full_name?: string
    phone?: string | null
    address?: string | null
  }) =>
    apiClient.patch<User>('/auth/me', data),
}
