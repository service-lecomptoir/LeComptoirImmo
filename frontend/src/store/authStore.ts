import { create } from 'zustand'
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

export const useAuthStore = create<AuthState>()((set, get) => ({
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

      // Stockage pour le client Axios (durée de session uniquement)
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
    // Effacement complet — aucune session persistée
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('lecomptoirimmo-auth')
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

  // Initialisation : valide le token stocké auprès du backend.
  // - Token valide  → reste connecté (refresh de page normal)
  // - Token absent/expiré → redirige vers /login
  // Cela évite la déconnexion sur F5 tout en garantissant qu'aucune session
  // périmée n'est acceptée sans validation serveur.
  initialize: async () => {
    const accessToken = localStorage.getItem('access_token')
    const refreshToken = localStorage.getItem('refresh_token')

    if (!accessToken) {
      // Aucun token stocké → pas de session
      set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isInitializing: false })
      return
    }

    try {
      // Valide le token en interrogeant le backend
      const { data: user } = await authApi.me()
      set({
        user,
        accessToken,
        refreshToken,
        isAuthenticated: true,
        isInitializing: false,
      })
    } catch {
      // Token invalide ou expiré → nettoyage propre
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isInitializing: false })
    }
  },
}))
