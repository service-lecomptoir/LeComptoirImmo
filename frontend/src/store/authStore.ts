import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Role } from '@/types/auth'
import { authApi } from '@/api/auth'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  isInitializing: boolean

  login: (email: string, password: string) => Promise<string>  // returns redirect path
  logout: () => void
  fetchMe: () => Promise<void>
  initialize: () => Promise<void>
}

export function roleHomePath(role: Role | undefined): string {
  if (role === 'locataire') return '/locataire'
  if (role === 'proprietaire') return '/proprietaire'
  return '/dashboard'
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      isInitializing: true,

      login: async (email, password) => {
        set({ isLoading: true })
        try {
          const { data } = await authApi.login({ email, password })

          // Stockage localStorage pour le client Axios
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)

          // Récupère le profil
          const { data: user } = await authApi.me()

          set({
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            user,
            isAuthenticated: true,
            isLoading: false,
          })

          return roleHomePath(user.role)
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      fetchMe: async () => {
        try {
          const { data } = await authApi.me()
          set({ user: data, isAuthenticated: true })
        } catch {
          get().logout()
        }
      },

      initialize: async () => {
        const { accessToken, fetchMe } = get()
        if (accessToken) {
          await fetchMe()
        }
        set({ isInitializing: false })
      },
    }),
    {
      name: 'lecomptoirimmo-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
