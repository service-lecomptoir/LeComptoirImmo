import { create } from 'zustand'
import type { Admin } from '@/types'
import { authApi } from '@/api/auth'

interface AuthState {
  admin: Admin | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  isInitializing: boolean

  login: (email: string, password: string) => Promise<void>
  logout: () => void
  initialize: () => Promise<void>
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  admin: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  isInitializing: true,

  login: async (email, password) => {
    set({ isLoading: true })
    try {
      const { data: tokenData } = await authApi.login(email, password)

      localStorage.setItem('alice_access_token', tokenData.access_token)

      const { data: admin } = await authApi.me()

      set({
        accessToken: tokenData.access_token,
        admin,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      set({ isLoading: false })
      throw error
    }
  },

  logout: () => {
    localStorage.removeItem('alice_access_token')
    set({
      admin: null,
      accessToken: null,
      isAuthenticated: false,
    })
  },

  initialize: async () => {
    const accessToken = localStorage.getItem('alice_access_token')

    if (!accessToken) {
      set({ isInitializing: false })
      return
    }

    try {
      const { data: admin } = await authApi.me()
      set({
        admin,
        accessToken,
        isAuthenticated: true,
        isInitializing: false,
      })
    } catch {
      localStorage.removeItem('alice_access_token')
      set({ admin: null, accessToken: null, isAuthenticated: false, isInitializing: false })
    }
  },
}))
