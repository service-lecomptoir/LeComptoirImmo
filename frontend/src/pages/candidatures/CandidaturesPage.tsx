import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui'
import { formatPhoneDisplay } from '@/utils/format'
import { Users, Plus, Trash2, X, Scale, BadgeCheck, ShieldQuestion, FileCheck2, Sparkles, Send, Link2, Download, Copy, CalendarClock, UserPlus, FileText } from 'lucide-react'
import { type VisitSlot } from '@/api/candidatures'
import { apiClient } from '@/api/client'
import { candidaturesApi, type Candidature, type CandidatureStatus } from '@/api/candidatures'
import { propertiesApi } from '@/api/properties'
import { toast } from '@/store/toast'
import { downloadBlob } from '@/utils/download'
import { useAuthStore } from '@/store/authStore'

interface Prop { id: string; name: string }

const STATUS: Record<CandidatureStatus, { label: string; cls: string }> = {
  nouvelle:           { label: 'Nouvelle',           cls: 'bg-blue-100 text-blue-700' },
  documents_demandes: { label: 'Pièces demandées',   cls: 'bg-indigo-100 text-indigo-700' },
  en_etude:           { label: 'En étude',           cls: 'bg-amber-100 text-amber-700' },
  retenue:            { label: 'Retenue',            cls: 'bg-emerald-100 text-emerald-700' },
  refusee:            { label: 'Refusée',            cls: 'bg-gray-200 text-gray-600' },
}

const pct = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v * 100)} %`)

export default function CandidaturesPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<Candidature[]>([])
  const [props, setProps] = useState<Prop[]>([])
  const [docLabels, setDocLabels] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [propertyId, setPropertyId] = useState('')
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState<Candidature | null>(null)
  const [showCompare, setShowCompare] = useState(false)
  const [compare, setCompare] = useState<{ rent_reference: number | null; candidates: Candidature[] } | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ property_id: '', first_name: '', last_name: '', email: '', phone: '', employment: '', monthly_income: '', has_guarantor: false, message: '' })
  const [busy, setBusy] = useState(false)
  // Propriétaire : accès en lecture seule (les écritures sont bloquées côté serveur).
  const readOnly = useAuthStore(s => s.user?.role === 'proprietaire')

  const load = async () => {
    setLoading(true)
    try {
      const [c, p] = await Promise.all([
        candidaturesApi.list({
          property_id: propertyId || undefined,
          status: status || undefined,
        }),
        propertiesApi.list({ limit: 200 }),
      ])
      setItems(c.data)
      setProps(((p.data as any).items ?? p.data) as Prop[])
    } catch { /* */ } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [propertyId, status])
  useEffect(() => {
    candidaturesApi.docKeys().then(r =>
      setDocLabels(Object.fromEntries(r.data.map(d => [d.key, d.label])))
    ).catch(() => {})
  }, [])

  const propName = useMemo(() => Object.fromEntries(props.map(p => [p.id, p.name])), [props])

  const patch = async (id: string, data: Parameters<typeof candidaturesApi.update>[1]) => {
    setBusy(true)
    try {
      const r = await candidaturesApi.update(id, data)
      setSelected(r.data)
      setItems(prev => prev.map(c => (c.id === id ? r.data : c)))
    } catch { /* */ } finally { setBusy(false) }
  }

  const toggleDoc = (c: Candidature, key: string, field: 'provided' | 'verified') => {
    const docs = c.docs.map(d => d.key === key ? { ...d, [field]: !d[field] } : d)
    patch(c.id, { docs })
  }

  // ── Demande de pièces (lien d'upload envoyé par e-mail) ──
  const [showRequest, setShowRequest] = useState(false)
  const [reqKeys, setReqKeys] = useState<Set<string>>(new Set())
  const [reqMessage, setReqMessage] = useState('')
  const [requesting, setRequesting] = useState(false)

  const openRequest = (c: Candidature) => {
    // Pré-cocher les pièces déjà marquées requises, sinon toutes les non fournies.
    const required = c.docs.filter(d => d.required).map(d => d.key)
    const base = required.length ? required : c.docs.filter(d => !d.provided).map(d => d.key)
    setReqKeys(new Set(base))
    setReqMessage('')
    setShowRequest(true)
  }
  const toggleReqKey = (key: string) => setReqKeys(prev => {
    const next = new Set(prev)
    next.has(key) ? next.delete(key) : next.add(key)
    return next
  })
  const sendRequest = async () => {
    if (!selected || reqKeys.size === 0) return
    setRequesting(true)
    try {
      const r = await candidaturesApi.requestDocuments(selected.id, {
        doc_keys: Array.from(reqKeys),
        message: reqMessage.trim() || null,
      })
      setSelected(r.data)
      setItems(prev => prev.map(c => (c.id === r.data.id ? r.data : c)))
      setShowRequest(false)
      toast.success(r.data.email_sent
        ? `Demande envoyée par e-mail à ${selected.email}.`
        : "Lien généré. L'e-mail n'a pas pu partir (SMTP) : copiez le lien et transmettez-le au candidat.")
    } catch { /* intercepteur */ } finally { setRequesting(false) }
  }

  const copyLink = (url?: string | null) => {
    if (!url) return
    navigator.clipboard?.writeText(url)
    toast.success('Lien copié.')
  }

  const downloadDoc = async (c: Candidature, key: string, filename?: string | null) => {
    try {
      const token = localStorage.getItem('access_token')
      const base = import.meta.env.VITE_API_URL || ''
      const r = await fetch(`${base}/api/v1${candidaturesApi.docDownloadUrl(c.id, key)}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) { toast.error('Pièce indisponible au téléchargement.'); return }
      downloadBlob(await r.blob(), filename || `${key}`)
    } catch {
      toast.error('Téléchargement impossible (erreur réseau).')
    }
  }

  // ── Visites ──
  const [showVisit, setShowVisit] = useState(false)
  const [slots, setSlots] = useState<VisitSlot[]>([])
  const [slotsLoading, setSlotsLoading] = useState(false)
  const [newSlot, setNewSlot] = useState({ starts_at: '', duration_min: '30', capacity: '1' })
  const [visitMsg, setVisitMsg] = useState('')
  const [visitBusy, setVisitBusy] = useState(false)

  const openVisit = async (c: Candidature) => {
    setShowVisit(true)
    setVisitMsg('')
    setSlotsLoading(true)
    try {
      const r = await candidaturesApi.visitSlots(c.property_id)
      setSlots(r.data)
    } catch { /* */ } finally { setSlotsLoading(false) }
  }
  const addSlot = async () => {
    if (!selected || !newSlot.starts_at) return
    setVisitBusy(true)
    try {
      await candidaturesApi.createVisitSlot({
        property_id: selected.property_id,
        starts_at: new Date(newSlot.starts_at).toISOString(),
        duration_min: Number(newSlot.duration_min) || 30,
        capacity: Number(newSlot.capacity) || 1,
      })
      const r = await candidaturesApi.visitSlots(selected.property_id)
      setSlots(r.data)
      setNewSlot({ starts_at: '', duration_min: '30', capacity: '1' })
    } catch { /* */ } finally { setVisitBusy(false) }
  }
  const removeSlot = async (slotId: string) => {
    if (!selected) return
    try {
      await candidaturesApi.deleteVisitSlot(slotId)
      setSlots(prev => prev.filter(s => s.id !== slotId))
    } catch { /* */ }
  }
  const sendVisitInvite = async () => {
    if (!selected) return
    setVisitBusy(true)
    try {
      const r = await candidaturesApi.inviteVisit(selected.id, { message: visitMsg.trim() || null })
      setSelected(r.data)
      setItems(prev => prev.map(c => (c.id === r.data.id ? r.data : c)))
      setShowVisit(false)
      toast.success(r.data.email_sent
        ? `Invitation envoyée à ${selected.email}.`
        : "Lien généré, mais e-mail non envoyé (SMTP) : copiez le lien de visite.")
    } catch { /* */ } finally { setVisitBusy(false) }
  }

  const acceptCandidate = async (c: Candidature) => {
    setBusy(true)
    try {
      const r = await candidaturesApi.accept(c.id, {})
      setSelected(r.data)
      setItems(prev => prev.map(x => (x.id === r.data.id ? r.data : x)))
      toast.success(r.data.email_sent
        ? "Candidat accepté : e-mail d'acceptation envoyé."
        : 'Candidat accepté (e-mail non envoyé : SMTP indisponible).')
    } catch { /* */ } finally { setBusy(false) }
  }

  const rejectCandidate = async (c: Candidature) => {
    setBusy(true)
    try {
      const r = await candidaturesApi.reject(c.id, {})
      setSelected(r.data)
      setItems(prev => prev.map(x => (x.id === r.data.id ? r.data : x)))
      toast.success(r.data.email_sent
        ? 'Candidat refusé : e-mail de refus courtois envoyé.'
        : 'Candidat refusé (e-mail non envoyé : pas d\'adresse ou SMTP indisponible).')
    } catch { /* */ } finally { setBusy(false) }
  }

  const acknowledgeCand = async (c: Candidature) => {
    setBusy(true)
    try {
      const r = await candidaturesApi.acknowledge(c.id)
      setSelected(r.data)
      setItems(prev => prev.map(x => (x.id === r.data.id ? r.data : x)))
      toast.success(r.data.email_sent
        ? `Accusé de réception envoyé à ${c.email}.`
        : 'Accusé de réception : e-mail non envoyé (SMTP indisponible).')
    } catch { /* */ } finally { setBusy(false) }
  }

  const remindVisitCand = async (c: Candidature) => {
    setBusy(true)
    try {
      const r = await candidaturesApi.remindVisit(c.id)
      setSelected(r.data)
      setItems(prev => prev.map(x => (x.id === r.data.id ? r.data : x)))
      toast.success(r.data.email_sent ? 'Relance de visite envoyée.' : 'Relance : e-mail non envoyé (SMTP indisponible).')
    } catch { /* */ } finally { setBusy(false) }
  }

  const toTenant = (c: Candidature) => {
    const parts = (c.full_name || '').trim().split(/\s+/)
    const first_name = parts.shift() || ''
    const last_name = parts.join(' ')
    navigate('/tenants', { state: { prefillTenant: { first_name, last_name, email: c.email || '', phone: c.phone || '' } } })
  }

  const remove = async (c: Candidature) => {
    if (!window.confirm(`Supprimer la candidature de ${c.full_name} ?`)) return
    try {
      await candidaturesApi.remove(c.id)
      setSelected(null)
      await load()
    } catch { /* */ }
  }

  const [comparePid, setComparePid] = useState('')
  const [cAi, setCAi] = useState<{ loading: boolean; text: string | null; disabled: boolean }>({ loading: false, text: null, disabled: false })
  const openCompare = async (pid: string) => {
    try {
      const r = await candidaturesApi.compare(pid)
      setCompare(r.data)
      setComparePid(pid)
      setCAi({ loading: false, text: null, disabled: false })
      setShowCompare(true)
    } catch { /* */ }
  }
  const runCompareAi = async () => {
    if (!comparePid) return
    setCAi({ loading: true, text: null, disabled: false })
    try {
      const { data } = await apiClient.get(`/candidatures/compare/${comparePid}/analysis`)
      setCAi({ loading: false, text: data.analysis || null, disabled: data.enabled === false })
    } catch {
      setCAi({ loading: false, text: null, disabled: false })
    }
  }

  const createManual = async (e: React.FormEvent) => {
    e.preventDefault()
    const fullName = `${form.first_name.trim()} ${form.last_name.trim()}`.trim()
    if (!form.property_id || !fullName) return
    setBusy(true)
    try {
      await candidaturesApi.create({
        property_id: form.property_id,
        full_name: fullName,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        employment: form.employment.trim() || null,
        monthly_income: form.monthly_income.trim() ? Number(form.monthly_income) : null,
        has_guarantor: form.has_guarantor,
        message: form.message.trim() || null,
      })
      toast.success('Candidature ajoutée.')
      setShowForm(false)
      setForm({ property_id: '', first_name: '', last_name: '', email: '', phone: '', employment: '', monthly_income: '', has_guarantor: false, message: '' })
      await load()
    } catch { /* */ } finally { setBusy(false) }
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><Users size={22} /> Candidatures</h1>
          <p className="text-gray-500 text-sm mt-1">
            Dossiers candidats centralisés : vérifiez les pièces, comparez les profils et sélectionnez le locataire le plus adapté.
          </p>
        </div>
        {readOnly ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-500 bg-gray-100 self-start">
            Lecture seule
          </span>
        ) : (
          <Button variant="primary" onClick={() => setShowForm(true)}
            className="rounded-xl font-semibold self-start" leftIcon={<Plus size={16} />}>
            Ajouter un dossier
          </Button>
        )}
      </div>

      {/* Filtres */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select value={propertyId} onChange={e => setPropertyId(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Tous les biens</option>
          {props.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Tous les statuts</option>
          {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        {propertyId && (
          <button onClick={() => openCompare(propertyId)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold bg-violet-100 hover:bg-violet-200 text-violet-700">
            <Scale size={15} /> Comparer les profils
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Liste */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center">
              <Users size={32} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm text-gray-400">Aucune candidature</p>
              <p className="text-xs text-gray-400 mt-1">Les dossiers déposés depuis vos annonces publiées arrivent ici.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {items.map(c => {
                const st = STATUS[c.status] ?? STATUS.nouvelle
                return (
                  <li key={c.id}>
                    <button onClick={() => setSelected(c)}
                      className={`w-full text-left px-4 py-3.5 hover:bg-gray-50 ${selected?.id === c.id ? 'bg-blue-50' : ''}`}>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900 truncate">{c.full_name}</p>
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${st.cls}`}>{st.label}</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{propName[c.property_id] ?? 'Bien'} · score {c.metrics.score}/100</p>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* Détail */}
        <div className="lg:col-span-2">
          {!selected ? (
            <div className="bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center h-64">
              <FileCheck2 size={36} className="text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Sélectionnez un dossier pour le vérifier et l'évaluer</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{selected.full_name}</h2>
                  <p className="text-sm text-gray-500">
                    {propName[selected.property_id] ?? 'Bien'} · {selected.source === 'annonce' ? "via l'annonce publique" : 'saisie manuelle'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${(STATUS[selected.status] ?? STATUS.nouvelle).cls}`}>
                    {(STATUS[selected.status] ?? STATUS.nouvelle).label}
                  </span>
                  {!readOnly && (
                    <button onClick={() => remove(selected)} className="p-1.5 text-red-400 hover:text-red-600" title="Supprimer">
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Indicateurs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Score</p>
                  <p className="text-lg font-bold text-gray-900">{selected.metrics.score}/100</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Taux d'effort</p>
                  <p className="text-lg font-bold text-gray-900">{pct(selected.metrics.effort_ratio)}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Dossier complet</p>
                  <p className="text-lg font-bold text-gray-900">{selected.metrics.completeness_pct} %</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Garant</p>
                  <p className="text-lg font-bold text-gray-900">{selected.has_guarantor ? 'Oui' : 'Non'}</p>
                </div>
              </div>

              {/* Coordonnées & situation */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                {selected.email && <p><span className="text-gray-400">E-mail :</span> <span className="text-gray-800">{selected.email}</span></p>}
                {selected.phone && <p><span className="text-gray-400">Téléphone :</span> <span className="text-gray-800">{formatPhoneDisplay(selected.phone)}</span></p>}
                {selected.employment && <p><span className="text-gray-400">Situation :</span> <span className="text-gray-800">{selected.employment}</span></p>}
                {selected.monthly_income != null && <p><span className="text-gray-400">Revenus :</span> <span className="text-gray-800">{selected.monthly_income.toLocaleString('fr-FR')} € / mois</span></p>}
              </div>
              {selected.message && (
                <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">{selected.message}</p>
              )}

              {/* Checklist des pièces */}
              <div>
                <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                  <h3 className="text-sm font-semibold text-gray-900">Pièces justificatives</h3>
                  {!readOnly && (
                    <button onClick={() => openRequest(selected)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-100 hover:bg-indigo-200 text-indigo-700">
                      <Send size={12} /> Demander des pièces
                    </button>
                  )}
                </div>

                {/* Lien public de dépôt (si une demande a été émise) */}
                {selected.upload_url && (
                  <div className="mb-3 flex items-center gap-2 rounded-lg border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs">
                    <Link2 size={13} className="text-indigo-600 shrink-0" />
                    <span className="truncate text-indigo-800 flex-1">{selected.upload_url}</span>
                    <button onClick={() => copyLink(selected.upload_url)}
                      className="inline-flex items-center gap-1 text-indigo-700 hover:text-indigo-900 font-semibold shrink-0">
                      <Copy size={12} /> Copier
                    </button>
                  </div>
                )}

                <ul className="space-y-1.5">
                  {selected.docs.map(d => (
                    <li key={d.key} className="flex items-center justify-between gap-3 text-sm bg-gray-50 rounded-lg px-3 py-2">
                      <span className="flex items-center gap-2 min-w-0">
                        <span className="text-gray-700 truncate">{d.label ?? docLabels[d.key] ?? d.key}</span>
                        {d.required && <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 shrink-0">Demandée</span>}
                        {d.has_file && (
                          <button onClick={() => downloadDoc(selected, d.key, d.filename)}
                            className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-800 shrink-0" title={d.filename || 'Télécharger'}>
                            <Download size={12} /> Voir
                          </button>
                        )}
                      </span>
                      <span className="flex items-center gap-2 shrink-0">
                        <button onClick={() => toggleDoc(selected, d.key, 'provided')} disabled={busy || readOnly}
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${readOnly ? 'cursor-default' : ''} ${d.provided ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-500'}`}>
                          {d.provided ? 'Fournie' : 'À fournir'}
                        </button>
                        <button onClick={() => toggleDoc(selected, d.key, 'verified')} disabled={busy || !d.provided || readOnly}
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full disabled:opacity-40 ${readOnly ? 'cursor-default' : ''} ${d.verified ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-500'}`}>
                          {d.verified ? 'Vérifiée ✓' : 'À vérifier'}
                        </button>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Notes */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Notes internes</h3>
                <textarea defaultValue={selected.notes ?? ''} rows={2} readOnly={readOnly}
                  onBlur={e => { if (!readOnly && (selected.notes ?? '') !== e.target.value) patch(selected.id, { notes: e.target.value || null }) }}
                  placeholder={readOnly ? 'Aucune note' : 'Vos observations sur ce dossier…'}
                  className={`w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none ${readOnly ? 'bg-gray-50 text-gray-600' : ''}`} />
              </div>

              {/* Statut de la visite */}
              {(selected.visit_booked_at || selected.visit_invited) && (
                <div className="flex items-center justify-between gap-2 text-xs rounded-lg bg-indigo-50 text-indigo-800 px-3 py-2 flex-wrap">
                  <span className="flex items-center gap-2">
                    <CalendarClock size={14} className="shrink-0" />
                    {selected.visit_booked_at
                      ? <span>Visite réservée le <strong>{new Date(selected.visit_booked_at).toLocaleString('fr-FR', { dateStyle: 'long', timeStyle: 'short' })}</strong>.</span>
                      : <span>Invitation à la visite envoyée. En attente de réservation par le candidat.</span>}
                  </span>
                  {!readOnly && selected.visit_booked_at && (
                    <button onClick={() => remindVisitCand(selected)} disabled={busy}
                      className="shrink-0 px-2.5 py-1 rounded-lg font-semibold bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-100 disabled:opacity-50">
                      Relancer avant la visite
                    </button>
                  )}
                </div>
              )}

              {/* Actions de statut */}
              <div className="flex flex-wrap gap-2 pt-1">
                {!readOnly && (<>
                  <button onClick={() => acknowledgeCand(selected)} disabled={busy || !selected.email}
                    title={selected.email ? '' : "Ce candidat n'a pas d'e-mail"}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-100 hover:bg-sky-200 text-sky-800 disabled:opacity-50">
                    <Send size={13} className="inline mr-1" />Accuser réception
                  </button>
                  <button onClick={() => patch(selected.id, { status: 'en_etude' })} disabled={busy || selected.status === 'en_etude'}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-100 hover:bg-amber-200 text-amber-800 disabled:opacity-50">
                    <ShieldQuestion size={13} className="inline mr-1" />Mettre en étude
                  </button>
                  <button onClick={() => openVisit(selected)} disabled={busy}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-100 hover:bg-indigo-200 text-indigo-800 disabled:opacity-50">
                    <CalendarClock size={13} className="inline mr-1" />Proposer une visite
                  </button>
                  <button onClick={() => acceptCandidate(selected)} disabled={busy || selected.status === 'retenue'}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-100 hover:bg-emerald-200 text-emerald-800 disabled:opacity-50">
                    <BadgeCheck size={13} className="inline mr-1" />Accepter le candidat
                  </button>
                  {selected.status === 'retenue' && (
                    <button onClick={() => toTenant(selected)} disabled={busy}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50">
                      <UserPlus size={13} className="inline mr-1" />Passer en locataire
                    </button>
                  )}
                  {selected.status === 'retenue' && (
                    <button onClick={() => navigate('/leases', { state: { prefillLease: { property_id: selected.property_id } } })} disabled={busy}
                      title="Créer le bail pour ce bien (le locataire et le loyer restent à confirmer)"
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50">
                      <FileText size={13} className="inline mr-1" />Créer le bail
                    </button>
                  )}
                  <button onClick={() => rejectCandidate(selected)} disabled={busy || selected.status === 'refusee'}
                    title={selected.email ? 'Refuser et envoyer un e-mail de refus courtois' : 'Refuser (pas d\'e-mail : aucun envoi)'}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-600 disabled:opacity-50">
                    Refuser{selected.email ? ' (avec e-mail)' : ''}
                  </button>
                </>)}
                <button onClick={() => openCompare(selected.property_id)}
                  className="ml-auto px-3 py-1.5 rounded-lg text-xs font-semibold bg-violet-100 hover:bg-violet-200 text-violet-700">
                  <Scale size={13} className="inline mr-1" />Comparer
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Modale comparaison ── */}
      {showCompare && compare && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowCompare(false)}>
          <div className="bg-white rounded-xl w-full max-w-3xl p-6 max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2"><Scale size={17} /> Comparaison des profils</h3>
              <button onClick={() => setShowCompare(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              {compare.rent_reference != null
                ? `Loyer de référence : ${compare.rent_reference.toLocaleString('fr-FR')} € (annonce du bien).`
                : "Renseignez le loyer dans l'annonce du bien pour calculer le taux d'effort."}
              {' '}Classement par score (effort, complétude du dossier, garant).
            </p>
            {compare.candidates.length > 0 && (
              <div className="mb-4 rounded-lg border border-violet-100 bg-violet-50/40 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-violet-800 flex items-center gap-1.5"><Sparkles size={15} /> Aide à la décision (IA)</span>
                  <button onClick={runCompareAi} disabled={cAi.loading}
                    className="text-xs px-3 py-1.5 rounded-lg bg-white border border-violet-200 text-violet-700 hover:bg-violet-50 disabled:opacity-50 whitespace-nowrap">
                    {cAi.loading ? 'Analyse…' : cAi.text ? 'Réactualiser' : 'Recommander un candidat'}
                  </button>
                </div>
                {cAi.disabled && <p className="text-sm text-gray-500 mt-2">L'assistant IA n'est pas activé sur la plateforme.</p>}
                {cAi.text && <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed mt-2">{cAi.text}</p>}
              </div>
            )}
            {compare.candidates.length === 0 ? (
              <p className="text-sm text-gray-400">Aucune candidature active pour ce bien.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-400 uppercase tracking-wide text-left">
                    <th className="py-2 pr-3 text-center">Candidat</th>
                    <th className="py-2 pr-3 text-center">Revenus</th>
                    <th className="py-2 pr-3 text-center">Effort</th>
                    <th className="py-2 pr-3 text-center">Dossier</th>
                    <th className="py-2 pr-3 text-center">Garant</th>
                    <th className="py-2 text-center">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {compare.candidates.map((c, i) => (
                    <tr key={c.id} className={`border-t border-gray-100 ${i === 0 ? 'bg-emerald-50/60' : ''}`}>
                      <td className="py-2.5 pr-3 text-center">
                        <span className="font-medium text-gray-900">{c.full_name}</span>
                        {i === 0 && <span className="ml-2 text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">Recommandé</span>}
                        <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${(STATUS[c.status] ?? STATUS.nouvelle).cls}`}>{(STATUS[c.status] ?? STATUS.nouvelle).label}</span>
                      </td>
                      <td className="py-2.5 pr-3 text-center">{c.monthly_income != null ? `${c.monthly_income.toLocaleString('fr-FR')} €` : '—'}</td>
                      <td className="py-2.5 pr-3 text-center">{pct(c.metrics.effort_ratio)}</td>
                      <td className="py-2.5 pr-3 text-center">{c.metrics.completeness_pct} %</td>
                      <td className="py-2.5 pr-3 text-center">{c.has_guarantor ? 'Oui' : 'Non'}</td>
                      <td className="py-2.5 font-bold text-gray-900 text-center">{c.metrics.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ── Modale ajout manuel ── */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Nouveau dossier candidat</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <form onSubmit={createManual} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <select required value={form.property_id} onChange={e => setForm(f => ({ ...f, property_id: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm sm:col-span-2">
                <option value="">Bien concerné *</option>
                {props.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input required placeholder="Prénom *" value={form.first_name}
                onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input required placeholder="Nom *" value={form.last_name}
                onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input type="email" placeholder="E-mail" value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Téléphone" value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Situation professionnelle" value={form.employment}
                onChange={e => setForm(f => ({ ...f, employment: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input type="number" min="0" placeholder="Revenus mensuels (€)" value={form.monthly_income}
                onChange={e => setForm(f => ({ ...f, monthly_income: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <label className="flex items-center gap-2 text-sm text-gray-700 px-1">
                <input type="checkbox" checked={form.has_guarantor}
                  onChange={e => setForm(f => ({ ...f, has_guarantor: e.target.checked }))} />
                A un garant
              </label>
              <textarea placeholder="Message / contexte" value={form.message} rows={2}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none sm:col-span-2" />
              <div className="sm:col-span-2 flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Annuler</button>
                <Button type="submit" variant="primary" isLoading={busy}
                  className="px-5 font-semibold">
                  {busy ? 'Enregistrement…' : 'Ajouter'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modale : demander des pièces ── */}
      {showRequest && selected && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-lg p-6 max-h-[88vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2"><Send size={17} /> Demander des pièces</h3>
              <button onClick={() => setShowRequest(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <p className="text-xs text-gray-500 mb-4">
              {selected.email
                ? <>Un e-mail avec un lien de dépôt sécurisé sera envoyé à <span className="font-medium text-gray-700">{selected.email}</span>.</>
                : <span className="text-red-600">Ce candidat n'a pas d'e-mail : renseignez-le d'abord (via la fiche) pour pouvoir envoyer la demande.</span>}
            </p>

            <div className="space-y-1.5 mb-4">
              {selected.docs.map(d => (
                <label key={d.key} className="flex items-center gap-2.5 text-sm bg-gray-50 rounded-lg px-3 py-2 cursor-pointer">
                  <input type="checkbox" checked={reqKeys.has(d.key)} onChange={() => toggleReqKey(d.key)} />
                  <span className="text-gray-700">{d.label ?? docLabels[d.key] ?? d.key}</span>
                  {d.provided && <span className="ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">déjà fournie</span>}
                </label>
              ))}
            </div>

            <textarea value={reqMessage} onChange={e => setReqMessage(e.target.value)} rows={3}
              placeholder="Message au candidat (facultatif) : précisions, délai souhaité…"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none mb-4" />

            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowRequest(false)}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Annuler</button>
              <Button variant="primary" onClick={sendRequest} isLoading={requesting}
                disabled={requesting || reqKeys.size === 0 || !selected.email}
                className="px-5 font-semibold" leftIcon={<Send size={15} />}>
                {requesting ? 'Envoi…' : 'Envoyer la demande'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modale : proposer une visite ── */}
      {showVisit && selected && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-lg p-6 max-h-[88vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2"><CalendarClock size={17} /> Proposer une visite</h3>
              <button onClick={() => setShowVisit(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <p className="text-xs text-gray-500 mb-4">
              Définissez des créneaux pour le bien <span className="font-medium text-gray-700">{selected.property_ref || propName[selected.property_id]}</span>,
              puis invitez le candidat. L'e-mail indique la référence et l'adresse du bien (pour s'y rendre), jamais le nom du logement, et précise qu'il y a d'autres candidats.
            </p>

            {/* Créneaux existants */}
            <div className="space-y-1.5 mb-3">
              {slotsLoading ? (
                <p className="text-sm text-gray-400">Chargement des créneaux…</p>
              ) : slots.length === 0 ? (
                <p className="text-sm text-gray-400">Aucun créneau pour ce bien. Ajoutez-en un ci-dessous.</p>
              ) : slots.map(s => (
                <div key={s.id} className="flex items-center justify-between gap-2 text-sm bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-gray-700">
                    {new Date(s.starts_at).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })}
                    <span className="text-gray-400"> · {s.duration_min} min · {s.booked_count}/{s.capacity} réservé(s)</span>
                  </span>
                  <button onClick={() => removeSlot(s.id)} className="text-red-400 hover:text-red-600 shrink-0" title="Supprimer">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>

            {/* Ajout d'un créneau */}
            <div className="flex flex-wrap items-end gap-2 mb-4 border-t border-gray-100 pt-3">
              <div className="flex-1 min-w-[180px]">
                <label className="block text-[11px] text-gray-500 mb-1">Date et heure</label>
                <input type="datetime-local" value={newSlot.starts_at}
                  onChange={e => setNewSlot(s => ({ ...s, starts_at: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" />
              </div>
              <div className="w-20">
                <label className="block text-[11px] text-gray-500 mb-1">Durée</label>
                <input type="number" min="5" step="5" value={newSlot.duration_min}
                  onChange={e => setNewSlot(s => ({ ...s, duration_min: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" />
              </div>
              <div className="w-20">
                <label className="block text-[11px] text-gray-500 mb-1">Places</label>
                <input type="number" min="1" value={newSlot.capacity}
                  onChange={e => setNewSlot(s => ({ ...s, capacity: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm" />
              </div>
              <button onClick={addSlot} disabled={visitBusy || !newSlot.starts_at}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-50">
                <Plus size={13} className="inline mr-1" />Ajouter
              </button>
            </div>

            <textarea value={visitMsg} onChange={e => setVisitMsg(e.target.value)} rows={2}
              placeholder="Message au candidat (facultatif)…"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none mb-4" />

            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowVisit(false)}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Fermer</button>
              <Button variant="primary" onClick={sendVisitInvite} isLoading={visitBusy}
                disabled={visitBusy || !selected.email || slots.length === 0}
                className="px-5 font-semibold" leftIcon={<Send size={15} />}>
                Inviter à réserver
              </Button>
            </div>
            {!selected.email && <p className="text-xs text-red-600 mt-2 text-right">Ce candidat n'a pas d'e-mail.</p>}
          </div>
        </div>
      )}
    </div>
  )
}
