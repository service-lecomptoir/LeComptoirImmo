import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
}

interface ToastState {
  toasts: ToastItem[]
  add: (type: ToastType, message: string) => void
  remove: (id: number) => void
}

let _seq = 1

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  add: (type, message) => {
    const id = _seq++
    set((s) => ({ toasts: [...s.toasts, { id, type, message }] }))
    // Auto-fermeture : les erreurs restent plus longtemps (à lire) que les succès.
    const ttl = type === 'error' ? 6000 : 3500
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, ttl)
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

/**
 * API impérative utilisable PARTOUT — y compris hors composants React
 * (ex. l'intercepteur axios dans api/client.ts). C'est le point d'entrée
 * unique pour afficher un message à l'utilisateur.
 */
export const toast = {
  success: (message: string) => useToastStore.getState().add('success', message),
  error: (message: string) => useToastStore.getState().add('error', message),
  info: (message: string) => useToastStore.getState().add('info', message),
}
