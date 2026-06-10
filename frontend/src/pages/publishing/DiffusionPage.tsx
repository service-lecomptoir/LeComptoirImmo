import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Megaphone, Plus, Trash2, Pencil, Building2, ChevronRight, X, Eye } from 'lucide-react'
import { publishingApi, type PublishPlatform, type PlatformKind, type ListingOverview } from '@/api/publishing'
import { propertiesApi } from '@/api/properties'
import { toast } from '@/store/toast'

const KIND_LABELS: Record<PlatformKind, string> = {
  reseau: 'Réseau social', site: 'Site web', email: 'E-mail de dépôt', lien: 'Lien', autre: 'Autre',
}
const KIND_HINT: Record<PlatformKind, string> = {
  reseau: 'URL de la page (Facebook, Instagram…)',
  site: "URL du site / portail",
  email: 'Adresse e-mail de dépôt des annonces',
  lien: 'URL libre (facultatif)',
  autre: 'Détail (facultatif)',
}

interface Prop { id: string; name: string; city?: string; zip_code?: string; reference?: string | null }

const EMPTY = { name: '', kind: 'site' as PlatformKind, target: '', is_active: true }

const LISTING_STATUS: Record<string, { label: string; cls: string }> = {
  draft:       { label: 'Brouillon',  cls: 'bg-gray-100 text-gray-600' },
  scheduled:   { label: 'Programmée', cls: 'bg-amber-100 text-amber-700' },
  published:   { label: 'Publiée',    cls: 'bg-emerald-100 text-emerald-700' },
  unpublished: { label: 'Dépubliée',  cls: 'bg-gray-200 text-gray-600' },
}

export default function DiffusionPage() {
  const [platforms, setPlatforms] = useState<PublishPlatform[]>([])
  const [overviews, setOverviews] = useState<Record<string, ListingOverview>>({})
  const [props, setProps] = useState<Prop[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [pf, pr, ov] = await Promise.all([
        publishingApi.listPlatforms(),
        propertiesApi.list({ limit: 200 }),
        publishingApi.listListings(),
      ])
      setPlatforms(pf.data)
      const items = (pr.data as any).items ?? pr.data
      setProps(items as Prop[])
      setOverviews(Object.fromEntries(ov.data.map(o => [o.property_id, o])))
    } catch { /* */ } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const openCreate = () => { setEditId(null); setForm(EMPTY); setShowForm(true) }
  const openEdit = (p: PublishPlatform) => {
    setEditId(p.id)
    setForm({ name: p.name, kind: p.kind, target: p.target ?? '', is_active: p.is_active })
    setShowForm(true)
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    try {
      const body = { name: form.name.trim(), kind: form.kind, target: form.target.trim() || null, is_active: form.is_active }
      if (editId) await publishingApi.updatePlatform(editId, body)
      else await publishingApi.createPlatform(body)
      toast.success(editId ? 'Plateforme modifiée.' : 'Plateforme ajoutée.')
      setShowForm(false)
      await load()
    } catch { /* */ } finally { setSaving(false) }
  }

  const remove = async (p: PublishPlatform) => {
    if (!window.confirm(`Supprimer la plateforme « ${p.name} » ?`)) return
    try { await publishingApi.deletePlatform(p.id); toast.success('Plateforme supprimée.'); await load() } catch { /* */ }
  }

  return (
    <div className="p-4 sm:p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><Megaphone size={22} /> Publication des annonces</h1>
        <p className="text-gray-500 text-sm mt-1">
          Créez et personnalisez vos annonces (photos, description, critères), diffusez-les sur vos plateformes, et suivez leurs performances (vues).
        </p>
      </div>

      {/* ── Plateformes ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Mes plateformes</h2>
          <button onClick={openCreate} className="inline-flex items-center gap-1.5 text-sm font-semibold text-white px-3 py-1.5 rounded-lg" style={{ background: '#0D2F5C' }}>
            <Plus size={15} /> Ajouter
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-400">Chargement…</p>
        ) : platforms.length === 0 ? (
          <p className="text-sm text-gray-400">Aucune plateforme. Ajoutez vos cibles de partage (réseaux, sites, e-mails de dépôt…).</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {platforms.map(p => (
              <li key={p.id} className="py-3 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">{p.name}</span>
                    {!p.is_active && <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">Inactive</span>}
                  </div>
                  <p className="text-xs text-gray-400 truncate">{KIND_LABELS[p.kind]}{p.target ? ` · ${p.target}` : ''}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button onClick={() => openEdit(p)} className="p-1.5 text-gray-400 hover:text-gray-700" title="Modifier"><Pencil size={15} /></button>
                  <button onClick={() => remove(p)} className="p-1.5 text-red-400 hover:text-red-600" title="Supprimer"><Trash2 size={15} /></button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ── Annonces par bien : statut + performances ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-4">Mes annonces</h2>
        {loading ? (
          <p className="text-sm text-gray-400">Chargement…</p>
        ) : props.length === 0 ? (
          <p className="text-sm text-gray-400">Aucun bien.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {props.map(p => {
              const ov = overviews[p.id]
              const st = ov ? (LISTING_STATUS[ov.status] ?? LISTING_STATUS.draft) : null
              return (
                <li key={p.id}>
                  <Link to={`/properties/${p.id}/publish`} className="py-3 flex items-center justify-between gap-3 hover:bg-gray-50 -mx-2 px-2 rounded-lg">
                    <div className="flex items-center gap-3 min-w-0">
                      <Building2 size={18} className="text-gray-400 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{p.name}</p>
                        <p className="text-xs text-gray-400 truncate">{[p.zip_code, p.city].filter(Boolean).join(' ')}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {ov && ov.status === 'published' && (
                        <span className="inline-flex items-center gap-1 text-xs text-gray-500" title="Vues de la page publique">
                          <Eye size={13} /> {ov.views_count}
                        </span>
                      )}
                      {st ? (
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span>
                      ) : (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-gray-50 text-gray-400">À créer</span>
                      )}
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600">Gérer <ChevronRight size={14} /></span>
                    </div>
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* ── Modale plateforme ── */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <div className="bg-white rounded-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">{editId ? 'Modifier la plateforme' : 'Nouvelle plateforme'}</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nom</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Ex. Page Facebook agence" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value as PlatformKind }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                  {(Object.keys(KIND_LABELS) as PlatformKind[]).map(k => <option key={k} value={k}>{KIND_LABELS[k]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cible</label>
                <input value={form.target} onChange={e => setForm(f => ({ ...f, target: e.target.value }))}
                  placeholder={KIND_HINT[form.kind]} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
                Active (proposée lors de la diffusion)
              </label>
              <div className="flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Annuler</button>
                <button type="submit" disabled={saving} className="px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-60" style={{ background: '#0D2F5C' }}>
                  {saving ? 'Enregistrement…' : 'Enregistrer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
