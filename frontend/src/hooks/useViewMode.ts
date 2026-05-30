import { useState, useCallback } from 'react'
import type { ViewMode } from '@/components/common/ViewToggle'

/**
 * Mémorise le mode d'affichage (liste/mosaïque) d'une page dans localStorage.
 * @param key   identifiant de la page (ex: "owners", "properties")
 * @param fallback mode par défaut si rien n'est mémorisé
 */
export function useViewMode(key: string, fallback: ViewMode = 'list'): [ViewMode, (v: ViewMode) => void] {
  const storageKey = `viewmode:${key}`
  const [mode, setModeState] = useState<ViewMode>(() => {
    try {
      const v = localStorage.getItem(storageKey)
      return v === 'grid' || v === 'list' ? v : fallback
    } catch {
      return fallback
    }
  })
  const setMode = useCallback((v: ViewMode) => {
    setModeState(v)
    try { localStorage.setItem(storageKey, v) } catch { /* ignore */ }
  }, [storageKey])
  return [mode, setMode]
}
