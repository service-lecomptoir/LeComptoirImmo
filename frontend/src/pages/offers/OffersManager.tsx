import { useState, useEffect, useRef } from 'react'
import { Plus, Pencil, Trash2, Tag, Euro, Phone, Image, Check, X, ToggleLeft, ToggleRight } from 'lucide-react'
import { offersApi, OFFER_CATEGORIES } from '@/api/offers'
import type { Offer, OfferCreate } from '@/api/offers'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  service:   { bg: 'bg-blue-50',   text: 'text-blue-700' },
  article:   { bg: 'bg-green-50',  text: 'text-green-700' },
  promotion: { bg: 'bg-orange-50', text: 'text-orange-700' },
  autre:     { bg: 'bg-gray-100',  text: 'text-gray-700' },
}

const EMPTY: OfferCreate = { title: '', description: '', price: undefined, category: 'service', contact_info: '', is_active: true }

function OfferForm({
  initial, onSave, onCancel,
}: { initial: OfferCreate; onSave: (data: OfferCreate) => Promise<void>; onCancel: () => void }) {
  const [form, setForm] = useState<OfferCreate>(initial)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const set = (k: keyof OfferCreate, v: any) => setForm(f => ({ ...f, [k]: v }))

  const handle = async () => {
    if (!form.title.trim()) { setError('Le titre est requis'); return }
    setSaving(true); setError('')
    try { await onSave(form) } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erreur')
    } finally { setSaving(false) }
  }

  const inp = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="block text-xs font-medium text-gray-600 mb-1">Titre *</label>
          <input value={form.title} onChange={e => set('title', e.target.value)} className={inp} placeholder="ex. Assurance habitation, Dépannage plomberie…" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Catégorie</label>
          <select value={form.category} onChange={e => set('category', e.target.value)} className={inp}>
            {OFFER_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Prix (€) — vide = sur demande</label>
          <input type="number" min={0} step={0.01} value={form.price ?? ''} onChange={e => set('price', e.target.value === '' ? undefined : Number(e.target.value))} className={inp} placeholder="0.00" />
        </div>
        <div className="col-span-2">
          <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <textarea value={form.description ?? ''} onChange={e => set('description', e.target.value)} rows={3} className={`${inp} resize-none`} placeholder="Décrivez l'offre ou le service proposé…" />
        </div>
        <div className="col-span-2">
          <label className="block text-xs font-medium text-gray-600 mb-1">Contact (téléphone, email, lien…)</label>
          <input value={form.contact_info ?? ''} onChange={e => set('contact_info', e.target.value)} className={inp} placeholder="06 XX XX XX XX · contact@exemple.fr" />
        </div>
        <div className="col-span-2 flex items-center gap-2">
          <input type="checkbox" id="is_active" checked={form.is_active ?? true} onChange={e => set('is_active', e.target.checked)} className="rounded" />
          <label htmlFor="is_active" className="text-sm text-gray-700">Visible par les locataires</label>
        </div>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2 justify-end">
        <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-100">Annuler</button>
        <button onClick={handle} disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">
          {saving ? <span className="animate-spin">⏳</span> : <Check size={14} />} Enregistrer
        </button>
      </div>
    </div>
  )
}

export default function OffersManager() {
  const [offers, setOffers] = useState<Offer[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadingId, setUploadingId] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    offersApi.list().then(r => setOffers(r.data)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const flash = (msg: string) => { setSuccessMsg(msg); setTimeout(() => setSuccessMsg(''), 3000) }

  const handleCreate = async (data: OfferCreate) => {
    const r = await offersApi.create(data)
    setOffers(prev => [r.data, ...prev])
    setCreating(false)
    flash('Offre créée')
  }

  const handleUpdate = async (id: string, data: OfferCreate) => {
    const r = await offersApi.update(id, data)
    setOffers(prev => prev.map(o => o.id === id ? r.data : o))
    setEditId(null)
    flash('Offre mise à jour')
  }

  const handleDelete = async (o: Offer) => {
    if (!confirm(`Supprimer "${o.title}" ?`)) return
    await offersApi.delete(o.id)
    setOffers(prev => prev.filter(x => x.id !== o.id))
    flash('Offre supprimée')
  }

  const handleToggle = async (o: Offer) => {
    const r = await offersApi.update(o.id, { is_active: !o.is_active })
    setOffers(prev => prev.map(x => x.id === o.id ? r.data : x))
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>, id: string) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingId(id)
    try {
      const r = await offersApi.uploadImage(id, file)
      setOffers(prev => prev.map(o => o.id === id ? r.data : o))
    } finally {
      setUploadingId(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const catLabel = (v: string) => OFFER_CATEGORIES.find(c => c.value === v)?.label ?? v

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Offres & Services</h1>
          <p className="text-sm text-gray-500 mt-1">Publiez des offres visibles par vos locataires</p>
        </div>
        {!creating && (
          <button onClick={() => setCreating(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={15} /> Nouvelle offre
          </button>
        )}
      </div>

      {successMsg && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800 flex items-center gap-2">
          <Check size={14} className="text-green-600" /> {successMsg}
        </div>
      )}

      {creating && (
        <div className="mb-6">
          <OfferForm initial={{ ...EMPTY }} onSave={handleCreate} onCancel={() => setCreating(false)} />
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400">Chargement…</div>
      ) : offers.length === 0 && !creating ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <Tag size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium">Aucune offre publiée</p>
          <p className="text-sm text-gray-400 mt-1">Créez votre première offre pour vos locataires.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {offers.map(o => (
            <div key={o.id} className={`bg-white rounded-xl border overflow-hidden ${!o.is_active ? 'opacity-60' : ''}`}>
              {editId === o.id ? (
                <div className="p-4">
                  <OfferForm
                    initial={{ title: o.title, description: o.description, price: o.price, category: o.category, contact_info: o.contact_info, is_active: o.is_active }}
                    onSave={data => handleUpdate(o.id, data)}
                    onCancel={() => setEditId(null)}
                  />
                </div>
              ) : (
                <div className="flex gap-4 p-4">
                  {/* Image */}
                  <div className="w-20 h-20 shrink-0 rounded-lg bg-gray-100 overflow-hidden relative group cursor-pointer"
                    onClick={() => { setUploadingId(o.id); fileInputRef.current?.click() }}>
                    {o.image_url ? (
                      <img src={`${API_BASE}${o.image_url}`} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-300">
                        <Image size={24} />
                      </div>
                    )}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                      <Image size={16} className="text-white" />
                    </div>
                    {uploadingId === o.id && (
                      <div className="absolute inset-0 bg-white/70 flex items-center justify-center">
                        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      </div>
                    )}
                  </div>

                  {/* Contenu */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-semibold text-gray-900 text-sm">{o.title}</p>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[o.category]?.bg ?? 'bg-gray-100'} ${CATEGORY_COLORS[o.category]?.text ?? 'text-gray-700'}`}>
                            {catLabel(o.category)}
                          </span>
                          {!o.is_active && <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">Masquée</span>}
                        </div>
                        {o.description && <p className="text-sm text-gray-600 mt-1 line-clamp-2">{o.description}</p>}
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          {o.price != null ? (
                            <span className="flex items-center gap-1"><Euro size={11} />{Number(o.price).toFixed(2)} €</span>
                          ) : (
                            <span className="text-gray-400">Prix sur demande</span>
                          )}
                          {o.contact_info && <span className="flex items-center gap-1"><Phone size={11} />{o.contact_info}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button onClick={() => handleToggle(o)} title={o.is_active ? 'Masquer' : 'Afficher'}
                          className="p-1.5 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50">
                          {o.is_active ? <ToggleRight size={16} className="text-blue-600" /> : <ToggleLeft size={16} />}
                        </button>
                        <button onClick={() => setEditId(o.id)} className="p-1.5 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50">
                          <Pencil size={14} />
                        </button>
                        <button onClick={() => handleDelete(o)} className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <input ref={fileInputRef} type="file" accept="image/*" className="hidden"
        onChange={e => uploadingId && handleImageUpload(e, uploadingId)} />
    </div>
  )
}
