import { create } from 'zustand'
import { subscriptionApi } from '@/api/subscription'

/**
 * Fonctionnalités autorisées par le plan du gestionnaire connecté.
 * `features === null` ⇒ aucune restriction (toutes autorisées / pas encore chargé).
 * Chargé une fois pour les rôles gestionnaire ; inerte pour les autres rôles.
 */
interface FeaturesState {
  features: string[] | null
  loaded: boolean
  loading: boolean
  loadFeatures: () => Promise<void>
  reset: () => void
}

export const useFeaturesStore = create<FeaturesState>((set, get) => ({
  features: null,
  loaded: false,
  loading: false,

  loadFeatures: async () => {
    if (get().loading || get().loaded) return
    set({ loading: true })
    try {
      const { data } = await subscriptionApi.get()
      set({ features: data.features ?? null, loaded: true, loading: false })
    } catch {
      // Fail-open : en cas d'échec on n'enferme pas l'utilisateur.
      set({ features: null, loaded: true, loading: false })
    }
  },

  reset: () => set({ features: null, loaded: false, loading: false }),
}))
