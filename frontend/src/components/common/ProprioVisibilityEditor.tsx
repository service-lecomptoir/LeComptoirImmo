import { useEffect, useState } from 'react'
import { Lock, Save } from 'lucide-react'
import { apiClient } from '@/api/client'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

interface CatalogSection { key: string; label: string; plan_allowed: boolean }

/**
 * Réglage des rubriques visibles par un propriétaire (lecture seule).
 * mode 'agency' : défaut appliqué à tous les propriétaires de l'agence.
 * mode 'owner'  : surcharge pour un propriétaire précis (0 rubrique = compte désactivé).
 * Les rubriques hors plan sont grisées et non cochables.
 */
export function ProprioVisibilityEditor({ mode, ownerUserId, onSaved }: {
  mode: 'agency' | 'owner'
  ownerUserId?: string
  onSaved?: () => void
}) {
  const [catalog, setCatalog] = useState<CatalogSection[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [isActive, setIsActive] = useState(true)
  const [usingDefault, setUsingDefault] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const { data: cat } = await apiClient.get('/users/proprio-visibility/catalog')
        if (cancelled) return
        setCatalog(cat.sections)
        if (mode === 'agency') {
          setSelected(new Set(cat.agency_default))
        } else if (ownerUserId) {
          const { data: v } = await apiClient.get(`/users/${ownerUserId}/proprio-visibility`)
          if (cancelled) return
          setIsActive(v.is_active)
          if (v.override) { setSelected(new Set(v.override)); setUsingDefault(false) }
          else { setSelected(new Set(cat.agency_default)); setUsingDefault(true) }
        }
      } catch { /* silencieux */ } finally { if (!cancelled) setLoading(false) }
    })()
    return () => { cancelled = true }
  }, [mode, ownerUserId])

  const toggle = (key: string) =>
    setSelected(prev => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n })

  const save = async () => {
    setSaving(true)
    try {
      const sections = Array.from(selected)
      if (mode === 'agency') {
        await apiClient.patch('/users/me/proprio-visibility-default', { sections })
        toast.success("Défaut d'agence enregistré")
      } else if (ownerUserId) {
        const { data } = await apiClient.patch(`/users/${ownerUserId}/proprio-visibility`, { sections })
        setIsActive(data.is_active); setUsingDefault(false)
        toast.success(data.is_active ? 'Visibilité enregistrée' : 'Aucune rubrique : compte propriétaire désactivé')
      }
      onSaved?.()
    } catch (e: any) {
      toast.error(getErrorMessage(e, 'Enregistrement impossible'))
    } finally { setSaving(false) }
  }

  if (loading) return <p className="text-sm text-gray-400">Chargement…</p>

  return (
    <div>
      {mode === 'owner' && usingDefault && (
        <p className="text-xs text-gray-400 mb-2">Aucun réglage spécifique : ce propriétaire suit le défaut d'agence.</p>
      )}
      {mode === 'owner' && !isActive && (
        <p className="text-xs text-red-600 mb-2 font-medium">Compte actuellement désactivé (aucune rubrique visible).</p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {catalog.map(s => (
          <label key={s.key}
            className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg border ${s.plan_allowed ? 'border-gray-200 cursor-pointer' : 'border-gray-100 bg-gray-50'}`}>
            <input type="checkbox" disabled={!s.plan_allowed}
              checked={s.plan_allowed && selected.has(s.key)} onChange={() => toggle(s.key)} />
            <span className={s.plan_allowed ? 'text-gray-800' : 'text-gray-400'}>{s.label}</span>
            {!s.plan_allowed && (
              <span className="ml-auto text-[10px] text-gray-400 inline-flex items-center gap-1"><Lock size={10} /> hors plan</span>
            )}
          </label>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-2">
        {mode === 'owner'
          ? 'Aucune rubrique cochée = compte propriétaire désactivé (plus d\'accès).'
          : 'Au moins une rubrique est requise. Les rubriques hors plan ne sont pas activables.'}
      </p>
      <div className="flex justify-end mt-3">
        <button onClick={save} disabled={saving}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
          <Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </div>
    </div>
  )
}
