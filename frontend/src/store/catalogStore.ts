import { create } from 'zustand'
import { apiClient } from '@/api/client'
import { FEATURE_LABELS, FEATURE_DESCRIPTIONS } from '@/lib/features'

/**
 * Catalogue PUBLIC des fonctionnalités, source de vérité unique.
 *
 * Récupéré depuis l'API Immo GET /api/v1/public/features (clé, libellé,
 * description, catégorie, ordre). Tout ce qui présente les fonctionnalités à
 * l'utilisateur (page Tarification, Guide, « Mon abonnement ») lit ce catalogue
 * → une fonctionnalité ajoutée, renommée ou re-décrite côté backend se reflète
 * partout sans modification de l'interface.
 *
 * État initial = repli statique (FEATURE_LABELS / FEATURE_DESCRIPTIONS) : tout
 * fonctionne avant le chargement et même si l'API est injoignable.
 */
export type Audience = 'all' | 'proprietaire' | 'mandataire'

export interface CatalogItem {
  key: string
  label: string
  description: string
  category: string
  order: number
  /** Profil ciblé ; défaut "all" (commune aux deux types de gestionnaire). */
  audience?: Audience
}

interface CatalogState {
  items: CatalogItem[]
  labels: Record<string, string>
  descriptions: Record<string, string>
  orderedKeys: string[]
  /** Audience par clé (défaut "all") — pour filtrer par type de plan. */
  audienceByKey: Record<string, Audience>
  loaded: boolean
  loading: boolean
  loadCatalog: () => Promise<void>
}

const FALLBACK_ITEMS: CatalogItem[] = Object.keys(FEATURE_LABELS).map((key, i) => ({
  key,
  label: FEATURE_LABELS[key],
  description: FEATURE_DESCRIPTIONS[key] ?? '',
  category: '',
  order: i,
}))

/** Index libellés/descriptions (fusionnés sur le repli → toujours complet). */
function index(items: CatalogItem[]) {
  const labels: Record<string, string> = { ...FEATURE_LABELS }
  const descriptions: Record<string, string> = { ...FEATURE_DESCRIPTIONS }
  const audienceByKey: Record<string, Audience> = {}
  for (const it of items) {
    labels[it.key] = it.label
    if (it.description) descriptions[it.key] = it.description
    audienceByKey[it.key] = it.audience || 'all'
  }
  return { labels, descriptions, orderedKeys: items.map(i => i.key), audienceByKey }
}

export const useCatalogStore = create<CatalogState>((set, get) => ({
  items: FALLBACK_ITEMS,
  ...index(FALLBACK_ITEMS),
  loaded: false,
  loading: false,

  loadCatalog: async () => {
    if (get().loading || get().loaded) return
    set({ loading: true })
    try {
      const { data } = await apiClient.get<CatalogItem[]>('/public/features')
      if (Array.isArray(data) && data.length) {
        const items = [...data].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
        set({ items, ...index(items), loaded: true, loading: false })
      } else {
        set({ loaded: true, loading: false })
      }
    } catch {
      // Repli silencieux : le catalogue statique reste en place.
      set({ loaded: true, loading: false })
    }
  },
}))
