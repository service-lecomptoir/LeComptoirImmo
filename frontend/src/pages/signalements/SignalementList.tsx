import { useEffect, useState } from 'react'
import {
  AlertTriangle, Download, MapPin, User, Clock, Filter, Building2, Moon, Bell,
} from 'lucide-react'
import { signalementsApi, type Signalement, type ProblemProperty, type SignalementStatus, type SignalementAlert } from '@/api/signalements'
import { apiClient } from '@/api/client'
import { Modal } from '@/components/common/Modal'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const URGENCY_BADGE: Record<string, string> = {
  faible: 'bg-gray-100 text-gray-600', moyen: 'bg-amber-100 text-amber-700', urgent: 'bg-red-100 text-red-700',
}
const STATUS_BADGE: Record<string, string> = {
  nouveau: 'bg-blue-100 text-blue-700', en_cours: 'bg-amber-100 text-amber-700',
  resolu: 'bg-green-100 text-green-700', clos: 'bg-gray-100 text-gray-600',
}
const STATUS_OPTIONS: { value: SignalementStatus; label: string }[] = [
  { value: 'nouveau', label: 'Nouveau' }, { value: 'en_cours', label: 'En cours' },
  { value: 'resolu', label: 'Résolu' }, { value: 'clos', label: 'Clos' },
]
const CATEGORY_OPTIONS = [
  ['bruit', 'Bruit'], ['securite', 'Sécurité'], ['proprete', 'Propreté'],
  ['logement', 'Logement'], ['degradation', 'Dégradation'], ['autre', 'Autre'],
]

export default function SignalementList() {
  const [tab, setTab] = useState<'liste' | 'logements' | 'alertes'>('liste')
  const [items, setItems] = useState<Signalement[]>([])
  const [problems, setProblems] = useState<ProblemProperty[]>([])
  const [alerts, setAlerts] = useState<SignalementAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [fStatus, setFStatus] = useState('')
  const [fCategory, setFCategory] = useState('')
  const [fUrgency, setFUrgency] = useState('')
  const [sel, setSel] = useState<Signalement | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (fStatus) params.status = fStatus
      if (fCategory) params.category = fCategory
      if (fUrgency) params.urgency = fUrgency
      const [{ data: list }, { data: pb }, { data: al }] = await Promise.all([
        signalementsApi.list(params),
        signalementsApi.problemProperties(),
        signalementsApi.alerts(),
      ])
      setItems(list.items); setProblems(pb); setAlerts(al)
    } catch { /* silencieux */ }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [fStatus, fCategory, fUrgency])

  const exportCsv = async () => {
    try {
      const params: any = {}
      if (fStatus) params.status = fStatus
      if (fCategory) params.category = fCategory
      const res = await apiClient.get(signalementsApi.exportUrl, { params, responseType: 'blob' })
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'signalements.csv'; a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) { toast.error(getErrorMessage(e, 'Export impossible')) }
  }

  const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <AlertTriangle size={22} className="text-amber-500" /> Signalements
          </h1>
          <p className="text-gray-500 text-sm mt-1">Problèmes remontés par vos locataires : suivi, logements à problème, historique.</p>
        </div>
        <button onClick={exportCsv}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700">
          <Download size={15} /> Export CSV
        </button>
      </div>

      {/* Onglets */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {([['liste', 'Liste'], ['logements', 'Logements à problème'], ['alertes', 'Alertes bruit']] as const).map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 transition-colors ${tab === k ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {l}
          </button>
        ))}
      </div>

      {tab === 'liste' ? (
        <>
          {/* Filtres */}
          <div className="flex items-center gap-2 mb-4 flex-wrap text-sm">
            <Filter size={15} className="text-gray-400" />
            <select value={fStatus} onChange={e => setFStatus(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg bg-white">
              <option value="">Tous statuts</option>
              {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <select value={fCategory} onChange={e => setFCategory(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg bg-white">
              <option value="">Toutes catégories</option>
              {CATEGORY_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <select value={fUrgency} onChange={e => setFUrgency(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg bg-white">
              <option value="">Toutes urgences</option>
              <option value="faible">Faible</option><option value="moyen">Moyen</option><option value="urgent">Urgent</option>
            </select>
          </div>

          {loading ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-gray-400">Aucun signalement.</p>
          ) : (
            <div className="space-y-2">
              {items.map(s => (
                <button key={s.id} onClick={() => setSel(s)}
                  className="w-full text-left bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-gray-900">{s.category_label}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${URGENCY_BADGE[s.urgency]}`}>{s.urgency_label}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[s.status]}`}>{s.status_label}</span>
                        {s.night_noise && <span className="px-2 py-0.5 rounded-full text-xs bg-indigo-100 text-indigo-700 inline-flex items-center gap-1"><Moon size={10} /> Nuit</span>}
                        {s.source === 'telematique' && <span className="px-2 py-0.5 rounded-full text-xs bg-violet-100 text-violet-700">Capteur</span>}
                      </div>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2 whitespace-pre-line">{s.description}</p>
                      <div className="flex items-center gap-3 text-xs text-gray-400 mt-1.5 flex-wrap">
                        {s.property_name && <span className="flex items-center gap-1"><MapPin size={11} /> {s.property_name}</span>}
                        {s.tenant_name && <span className="flex items-center gap-1"><User size={11} /> {s.tenant_name}</span>}
                        {s.occurred_at && <span className="flex items-center gap-1"><Clock size={11} /> {format(new Date(s.occurred_at), 'd MMM HH:mm', { locale: fr })}</span>}
                      </div>
                    </div>
                    {s.photo_url && <img src={`${API_BASE}${s.photo_url}`} alt="" className="w-14 h-14 object-cover rounded-lg border border-gray-200 shrink-0" />}
                  </div>
                </button>
              ))}
            </div>
          )}
        </>
      ) : tab === 'logements' ? (
        <>
          {loading ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : problems.length === 0 ? (
            <p className="text-sm text-gray-400">Aucun logement avec signalement.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {problems.map(p => (
                <div key={p.property_id} className="bg-white rounded-xl border border-gray-200 p-4">
                  <div className="flex items-start gap-2">
                    <Building2 size={18} className="text-gray-400 mt-0.5 shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 truncate">{p.property_name}</p>
                      {p.property_address && <p className="text-xs text-gray-400 whitespace-pre-line leading-tight">{p.property_address}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-3 text-xs flex-wrap">
                    <span className="px-2 py-1 rounded-lg bg-gray-100 text-gray-700">{p.total} au total</span>
                    {p.ouverts > 0 && <span className="px-2 py-1 rounded-lg bg-amber-100 text-amber-700">{p.ouverts} ouvert{p.ouverts > 1 ? 's' : ''}</span>}
                    {p.bruit > 0 && <span className="px-2 py-1 rounded-lg bg-blue-100 text-blue-700">{p.bruit} bruit</span>}
                    {p.urgents > 0 && <span className="px-2 py-1 rounded-lg bg-red-100 text-red-700">{p.urgents} urgent{p.urgents > 1 ? 's' : ''}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <>
          <p className="text-xs text-gray-400 mb-3 flex items-center gap-1.5">
            <Bell size={13} /> Alertes automatiques du moteur bruit : message nocturne (22h-7h) à l'appartement, escalade en cas de récurrence, rappels préventifs.
          </p>
          {loading ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : alerts.length === 0 ? (
            <p className="text-sm text-gray-400">Aucune alerte pour le moment.</p>
          ) : (
            <div className="space-y-2">
              {alerts.map(a => {
                const cls = a.alert_type === 'escalade' ? 'bg-red-100 text-red-700'
                  : a.alert_type === 'nocturne' ? 'bg-indigo-100 text-indigo-700'
                  : 'bg-emerald-100 text-emerald-700'
                const Icon = a.alert_type === 'escalade' ? AlertTriangle : a.alert_type === 'nocturne' ? Moon : Bell
                return (
                  <div key={a.id} className="bg-white rounded-xl border border-gray-200 p-3 flex items-start gap-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium inline-flex items-center gap-1 shrink-0 ${cls}`}>
                      <Icon size={11} /> {a.alert_label}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm text-gray-700">{a.message}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {a.property_name ? a.property_name + ' · ' : ''}{format(new Date(a.created_at), 'd MMM yyyy à HH:mm', { locale: fr })}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {sel && (
        <SignalementDetail s={sel} onClose={() => setSel(null)} onSaved={() => { setSel(null); load() }} apiBase={API_BASE} />
      )}
    </div>
  )
}

function SignalementDetail({ s, onClose, onSaved, apiBase }: { s: Signalement; onClose: () => void; onSaved: () => void; apiBase: string }) {
  const [status, setStatus] = useState<SignalementStatus>(s.status)
  const [urgency, setUrgency] = useState(s.urgency)
  const [note, setNote] = useState(s.resolution_note || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      await signalementsApi.update(s.id, { status, urgency: urgency as any, resolution_note: note.trim() || null })
      onSaved()
    } catch (e: any) { toast.error(getErrorMessage(e, 'Enregistrement impossible')) }
    finally { setSaving(false) }
  }

  return (
    <Modal isOpen onClose={onClose} title={s.category_label} size="lg"
      footer={
        <>
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">Fermer</button>
          <button onClick={save} disabled={saving} className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </>
      }>
      <div className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap text-sm text-gray-500">
          {s.night_noise && <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 inline-flex items-center gap-1"><Moon size={11} /> Bruit nocturne</span>}
          {s.property_name && <span className="flex items-center gap-1"><MapPin size={13} /> {s.property_name}</span>}
          {s.tenant_name && <span className="flex items-center gap-1"><User size={13} /> {s.tenant_name}</span>}
          <span className="flex items-center gap-1"><Clock size={13} /> {s.occurred_at ? format(new Date(s.occurred_at), 'd MMM yyyy à HH:mm', { locale: fr }) : '—'}</span>
        </div>
        <p className="text-sm text-gray-800 whitespace-pre-line">{s.description}</p>
        {s.photo_url && (
          <a href={`${apiBase}${s.photo_url}`} target="_blank" rel="noreferrer">
            <img src={`${apiBase}${s.photo_url}`} alt="photo" className="max-h-64 rounded-lg border border-gray-200" />
          </a>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-gray-100">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Statut</label>
            <select value={status} onChange={e => setStatus(e.target.value as SignalementStatus)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Urgence</label>
            <select value={urgency} onChange={e => setUrgency(e.target.value as any)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="faible">Faible</option><option value="moyen">Moyen</option><option value="urgent">Urgent</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Réponse / note de traitement (visible par le locataire)</label>
          <textarea value={note} onChange={e => setNote(e.target.value)} rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
        </div>
      </div>
    </Modal>
  )
}
