import { useState, useEffect } from 'react'
import { formatPhoneDisplay } from '@/utils/format'
import { BRAND } from '@/lib/brand'
import { Wrench, Plus, Pencil, Trash2, X } from 'lucide-react'
import { entretiensApi, prestatairesApi, type Entretien, type Prestataire } from '@/api/entretiens'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  planifie:  { label: 'Planifié',   color: '#2563EB', bg: '#DBEAFE' },
  en_cours:  { label: 'En cours',   color: '#D97706', bg: '#FEF3C7' },
  termine:   { label: 'Terminé',    color: '#059669', bg: '#D1FAE5' },
  annule:    { label: 'Annulé',     color: '#6B7280', bg: '#F3F4F6' },
}

const TYPE_LABELS: Record<string, string> = {
  preventif:  '🔧 Préventif',
  correctif:  '🚨 Correctif',
  inspection: '🔍 Inspection',
}

const FREQ_LABELS: Record<string, string> = {
  unique:       'Unique',
  mensuel:      'Mensuel',
  trimestriel:  'Trimestriel',
  semestriel:   'Semestriel',
  annuel:       'Annuel',
}

const fmtEuro = (n: number) => n.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €'

interface EntretienFormData {
  title: string
  description: string
  type: string
  status: string
  frequency: string
  scheduled_date: string
  completed_date: string
  next_date: string
  cost: string
  prestataire_id: string
  notes: string
}

const DEFAULT_FORM: EntretienFormData = {
  title: '', description: '', type: 'preventif', status: 'planifie',
  frequency: 'unique', scheduled_date: '', completed_date: '',
  next_date: '', cost: '', prestataire_id: '', notes: '',
}

export default function EntretienList({ readOnly = false }: { readOnly?: boolean }) {
  const [entretiens, setEntretiens] = useState<Entretien[]>([])
  const [prestataires, setPrestataires] = useState<Prestataire[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState<EntretienFormData>(DEFAULT_FORM)
  const [isSaving, setIsSaving] = useState(false)
  const [selected, setSelected] = useState<Entretien | null>(null)
  const [tab, setTab] = useState<'liste' | 'prestataires'>('liste')
  const [autoplanMsg, setAutoplanMsg] = useState<string | null>(null)

  // Prestataires form
  const [showPrestForm, setShowPrestForm] = useState(false)
  const [prestForm, setPrestForm] = useState({ name: '', specialty: '', phone: '', email: '', siret: '', notes: '' })
  const [isSavingPrest, setIsSavingPrest] = useState(false)

  const load = async () => {
    setIsLoading(true)
    try {
      const [eRes, pRes] = await Promise.allSettled([
        entretiensApi.list({ status: filter || undefined }),
        prestatairesApi.list(false),
      ])
      if (eRes.status === 'fulfilled') {
        setEntretiens(eRes.value.data.items)
        setTotal(eRes.value.data.total)
      }
      if (pRes.status === 'fulfilled') setPrestataires(pRes.value.data)
    } finally { setIsLoading(false) }
  }

  useEffect(() => { load() }, [filter])

  // Planification automatique d'après l'historique (au montage, hors lecture seule).
  useEffect(() => {
    if (readOnly) return
    let cancelled = false
    entretiensApi.autoplan()
      .then(res => {
        if (cancelled || !res.data.created) return
        const n = res.data.created
        setAutoplanMsg(`${n} maintenance${n > 1 ? 's' : ''} planifiée${n > 1 ? 's' : ''} automatiquement d'après l'historique.`)
        load()
      })
      .catch(() => { /* silencieux */ })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    try {
      const payload: any = {
        title: form.title,
        description: form.description || undefined,
        type: form.type,
        status: form.status,
        frequency: form.frequency,
        scheduled_date: form.scheduled_date,
        completed_date: form.completed_date || undefined,
        next_date: form.next_date || undefined,
        cost: form.cost ? parseFloat(form.cost) : undefined,
        prestataire_id: form.prestataire_id || undefined,
        notes: form.notes || undefined,
      }
      if (editId) {
        await entretiensApi.update(editId, payload)
      } else {
        await entretiensApi.create(payload)
      }
      setShowForm(false)
      setEditId(null)
      setForm(DEFAULT_FORM)
      await load()
    } finally { setIsSaving(false) }
  }

  const handleEdit = (e: Entretien) => {
    setForm({
      title: e.title,
      description: e.description ?? '',
      type: e.type,
      status: e.status,
      frequency: e.frequency,
      scheduled_date: e.scheduled_date,
      completed_date: e.completed_date ?? '',
      next_date: e.next_date ?? '',
      cost: e.cost ? String(e.cost) : '',
      prestataire_id: e.prestataire_id ?? '',
      notes: e.notes ?? '',
    })
    setEditId(e.id)
    setShowForm(true)
    setSelected(null)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Supprimer cet entretien ?')) return
    await entretiensApi.delete(id)
    setSelected(null)
    await load()
  }

  const handleCreatePrest = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSavingPrest(true)
    try {
      await prestatairesApi.create(prestForm)
      setShowPrestForm(false)
      setPrestForm({ name: '', specialty: '', phone: '', email: '', siret: '', notes: '' })
      await load()
    } finally { setIsSavingPrest(false) }
  }

  const FILTERS = [
    { value: '', label: 'Tous' },
    { value: 'planifie', label: 'Planifiés' },
    { value: 'en_cours', label: 'En cours' },
    { value: 'termine', label: 'Terminés' },
    { value: 'annule', label: 'Annulés' },
  ]

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Entretiens & maintenance</h1>
          <p className="text-gray-500 text-sm mt-1">Planification, prestataires et suivi</p>
        </div>
        {!readOnly && tab === 'liste' && (
          <button
            onClick={() => { setShowForm(true); setEditId(null); setForm(DEFAULT_FORM) }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white"
            style={{ background: BRAND.navy }}
          >
            <Plus size={16} />
            Nouvel entretien
          </button>
        )}
      </div>

      {/* Onglets */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        {(['liste', 'prestataires'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className="px-4 py-1.5 rounded-md text-sm font-medium transition-all"
            style={{ background: tab === t ? '#FFFFFF' : 'transparent', color: tab === t ? BRAND.navy : '#6B7280', boxShadow: tab === t ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}>
            {t === 'liste' ? 'Entretiens' : 'Prestataires'}
          </button>
        ))}
      </div>

      {tab === 'liste' && autoplanMsg && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border px-4 py-3 text-sm"
          style={{ background: '#ECFDF5', borderColor: '#A7F3D0', color: '#0f766e' }}>
          <Wrench size={16} className="mt-0.5 shrink-0" />
          <div className="flex-1">
            <b>Planification automatique</b> : {autoplanMsg} Les entretiens créés portent le badge « Auto ».
          </div>
          <button onClick={() => setAutoplanMsg(null)} className="text-teal-700 hover:text-teal-900">
            <X size={15} />
          </button>
        </div>
      )}

      {tab === 'prestataires' ? (
        <div>
          {!readOnly && (
            <div className="mb-4 flex justify-end">
              <button onClick={() => setShowPrestForm(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white"
                style={{ background: BRAND.navy }}>
                <Plus size={16} /> Ajouter un prestataire
              </button>
            </div>
          )}
          {showPrestForm && !readOnly && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
              <h3 className="font-semibold text-gray-900 mb-4">Nouveau prestataire</h3>
              <form onSubmit={handleCreatePrest} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Nom *</label>
                  <input value={prestForm.name} onChange={e => setPrestForm(p => ({ ...p, name: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" required />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Spécialité</label>
                  <input value={prestForm.specialty} onChange={e => setPrestForm(p => ({ ...p, specialty: e.target.value }))}
                    placeholder="Plombier, électricien…" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Téléphone</label>
                  <input value={prestForm.phone} onChange={e => setPrestForm(p => ({ ...p, phone: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                  <input value={prestForm.email} onChange={e => setPrestForm(p => ({ ...p, email: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">SIRET</label>
                  <input value={prestForm.siret} onChange={e => setPrestForm(p => ({ ...p, siret: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div className="col-span-2 flex gap-3 justify-end">
                  <button type="button" onClick={() => setShowPrestForm(false)}
                    className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg">Annuler</button>
                  <button type="submit" disabled={isSavingPrest}
                    className="px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-60"
                    style={{ background: BRAND.navy }}>{isSavingPrest ? 'Enregistrement…' : 'Enregistrer'}</button>
                </div>
              </form>
            </div>
          )}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {prestataires.length === 0 ? (
              <div className="py-12 text-center text-gray-400 text-sm">Aucun prestataire</div>
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {['Nom', 'Spécialité', 'Téléphone', 'Email', 'Statut'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {prestataires.map(p => (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{p.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{p.specialty ?? ''}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{formatPhoneDisplay(p.phone)}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{p.email ?? ''}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${p.is_active ? 'text-green-700 bg-green-100' : 'text-gray-500 bg-gray-100'}`}>
                          {p.is_active ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* Formulaire entretien */}
          {showForm && !readOnly && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">{editId ? 'Modifier l\'entretien' : 'Nouvel entretien'}</h3>
                <button onClick={() => { setShowForm(false); setEditId(null) }}><X size={18} className="text-gray-400" /></button>
              </div>
              <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Titre *</label>
                  <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                    placeholder="Ex: Révision chaudière" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" required />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                  <select value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                    <option value="preventif">Préventif</option>
                    <option value="correctif">Correctif</option>
                    <option value="inspection">Inspection</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Fréquence</label>
                  <select value={form.frequency} onChange={e => setForm(f => ({ ...f, frequency: e.target.value }))} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                    {Object.entries(FREQ_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Statut</label>
                  <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                    {Object.entries(STATUS_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Prestataire</label>
                  <select value={form.prestataire_id} onChange={e => setForm(f => ({ ...f, prestataire_id: e.target.value }))} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                    <option value="">Aucun</option>
                    {prestataires.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Date planifiée *</label>
                  <input type="date" value={form.scheduled_date} onChange={e => setForm(f => ({ ...f, scheduled_date: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" required />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Date réalisation</label>
                  <input type="date" value={form.completed_date} onChange={e => setForm(f => ({ ...f, completed_date: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Prochaine date</label>
                  <input type="date" value={form.next_date} onChange={e => setForm(f => ({ ...f, next_date: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Coût (€)</label>
                  <input type="number" step="0.01" value={form.cost} onChange={e => setForm(f => ({ ...f, cost: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                  <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                    rows={2} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none" />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                  <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                    rows={2} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none" />
                </div>
                <div className="col-span-2 flex gap-3 justify-end">
                  <button type="button" onClick={() => { setShowForm(false); setEditId(null) }}
                    className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg">Annuler</button>
                  <button type="submit" disabled={isSaving}
                    className="px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-60"
                    style={{ background: BRAND.navy }}>{isSaving ? 'Enregistrement…' : editId ? 'Modifier' : 'Créer'}</button>
                </div>
              </form>
            </div>
          )}

          {/* Filtres */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {FILTERS.map(f => (
              <button key={f.value} onClick={() => setFilter(f.value)}
                className="px-3 py-1.5 rounded-full text-sm font-medium transition-all"
                style={{ background: filter === f.value ? BRAND.navy : '#F1F5F9', color: filter === f.value ? '#FFFFFF' : '#475569' }}>
                {f.label}
              </button>
            ))}
            <span className="ml-auto text-sm text-gray-400 self-center">{total} entretien{total > 1 ? 's' : ''}</span>
          </div>

          {/* Table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {isLoading ? (
              <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
            ) : entretiens.length === 0 ? (
              <div className="py-12 text-center">
                <Wrench size={32} className="mx-auto mb-2 text-gray-300" />
                <p className="text-sm text-gray-400">Aucun entretien planifié</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {['Titre', 'Type', 'Date', 'Prestataire', 'Coût', 'Statut', ...(readOnly ? [] : [''])].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {entretiens.map(e => {
                    const sc = STATUS_CONFIG[e.status] ?? STATUS_CONFIG.planifie
                    return (
                      <tr key={e.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(s => s?.id === e.id ? null : e)}>
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-gray-900">
                            {e.title}
                            {e.notes?.startsWith('[auto]') && (
                              <span className="ml-2 align-middle text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                                style={{ color: '#0E9F8E', background: '#D1FAE5' }} title="Planifié automatiquement d'après l'historique">
                                Auto
                              </span>
                            )}
                          </p>
                          {e.property_label && <p className="text-xs text-gray-400">{e.property_label}</p>}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">{TYPE_LABELS[e.type]}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {format(new Date(e.scheduled_date), 'd MMM yyyy', { locale: fr })}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">{e.prestataire_name ?? ''}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{e.cost ? fmtEuro(e.cost) : ''}</td>
                        <td className="px-4 py-3">
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                            style={{ color: sc.color, background: sc.bg }}>{sc.label}</span>
                        </td>
                        {!readOnly && (
                          <td className="px-4 py-3">
                            <div className="flex gap-2" onClick={ev => ev.stopPropagation()}>
                              <button onClick={() => handleEdit(e)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-blue-600">
                                <Pencil size={14} />
                              </button>
                              <button onClick={() => handleDelete(e.id)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-red-500">
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              </div>
            )}
          </div>

          {/* Détail inline */}
          {selected && (
            <div className="mt-4 bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-900">{selected.title}</h3>
                <button onClick={() => setSelected(null)}><X size={16} className="text-gray-400" /></button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div><p className="text-xs text-gray-400">Type</p><p className="font-medium">{TYPE_LABELS[selected.type]}</p></div>
                <div><p className="text-xs text-gray-400">Fréquence</p><p className="font-medium">{FREQ_LABELS[selected.frequency]}</p></div>
                <div><p className="text-xs text-gray-400">Date planifiée</p><p className="font-medium">{format(new Date(selected.scheduled_date), 'd MMMM yyyy', { locale: fr })}</p></div>
                {selected.completed_date && <div><p className="text-xs text-gray-400">Réalisé le</p><p className="font-medium text-green-600">{format(new Date(selected.completed_date), 'd MMMM yyyy', { locale: fr })}</p></div>}
                {selected.next_date && <div><p className="text-xs text-gray-400">Prochaine intervention</p><p className="font-medium">{format(new Date(selected.next_date), 'd MMMM yyyy', { locale: fr })}</p></div>}
                {selected.prestataire_name && <div><p className="text-xs text-gray-400">Prestataire</p><p className="font-medium">{selected.prestataire_name}</p></div>}
                {selected.cost != null && <div><p className="text-xs text-gray-400">Coût</p><p className="font-medium">{fmtEuro(selected.cost)}</p></div>}
                {selected.property_label && <div><p className="text-xs text-gray-400">Bien</p><p className="font-medium">{selected.property_label}</p></div>}
              </div>
              {selected.description && <p className="mt-3 text-sm text-gray-600 border-t border-gray-100 pt-3">{selected.description}</p>}
              {selected.notes && <p className="mt-2 text-xs text-gray-400 italic">{selected.notes}</p>}
            </div>
          )}
        </>
      )}
    </div>
  )
}
