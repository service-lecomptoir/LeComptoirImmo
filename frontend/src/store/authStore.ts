import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types/auth'
import { authApi } from '@/api/auth'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean

  login: (email: string, password: string) => Promise<void>
  logout: () => void
  fetchMe: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

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
    }),
    {
      name: 'locataire-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
