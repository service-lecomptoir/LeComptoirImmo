import { useState, useEffect } from 'react'
import { BRAND } from '@/lib/brand'
import { Button } from '@/components/ui'
import { getErrorMessage } from '@/utils/errors'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, Edit, FileDown, XCircle,
  Home, User, Calendar, CreditCard, ShieldCheck, StickyNote, ClipboardList, Plus,
  HeartHandshake, Trash2, DoorOpen, TrendingUp,
} from 'lucide-react'
import { leasesApi, type RentRevision } from '@/api/leases'
import { toast } from '@/store/toast'
import { scoringApi, type RelationEvent, type EventKind } from '@/api/scoring'
import { inspectionsApi } from '@/api/inspections'
import { StatusBadge } from '@/components/common/StatusBadge'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { LeaseForm } from './LeaseForm'
import { LEASE_TYPE_LABELS, RENT_CALL_RULE_LABELS, PAYMENT_FREQUENCY_LABELS } from '@/types/lease'
import { docFilename } from '@/utils/filename'
import { formatNir, formatPhoneDisplay } from '@/utils/format'
import {
  INSPECTION_TYPE_LABELS,
  CONDITION_LABELS,
  CONDITION_VARIANTS,
} from '@/types/inspection'
import type { Lease } from '@/types/lease'
import type { Inspection } from '@/types/inspection'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

// ── Section « Relation locataire » (alimente le scoring) ─────────────────────
const _POLARITY: Record<string, { color: string; bg: string }> = {
  positif: { color: BRAND.teal, bg: '#D1FAE5' },
  negatif: { color: '#DC2626', bg: '#FEE2E2' },
  neutre:  { color: '#6B7280', bg: '#F3F4F6' },
}

function RelationSection({ leaseId, canEdit }: { leaseId: string; canEdit: boolean }) {
  const [events, setEvents] = useState<RelationEvent[]>([])
  const [kinds, setKinds] = useState<EventKind[]>([])
  const [form, setForm] = useState({ kind: '', note: '' })
  const [saving, setSaving] = useState(false)

  const load = () => { scoringApi.listEvents(leaseId).then(r => setEvents(r.data)).catch(() => {}) }
  useEffect(() => { load(); scoringApi.eventKinds().then(r => setKinds(r.data)).catch(() => {}) }, [leaseId])

  const add = async () => {
    if (!form.kind) return
    setSaving(true)
    try {
      const r = await scoringApi.addEvent(leaseId, { kind: form.kind, note: form.note || undefined })
      setEvents(r.data); setForm({ kind: '', note: '' })
    } finally { setSaving(false) }
  }
  const del = async (id: string) => { const r = await scoringApi.deleteEvent(leaseId, id); setEvents(r.data) }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 md:col-span-2">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-1">
        <HeartHandshake size={15} className="text-blue-500" /> Relation locataire
      </h2>
      <p className="text-xs text-gray-400 mb-3">Événements de suivi pris en compte dans le score de qualité de payeur.</p>

      {canEdit && (
        <div className="flex flex-col sm:flex-row gap-2 mb-3">
          <select value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value }))}
            className="border border-gray-200 rounded-lg px-2 py-2 text-sm sm:w-56">
            <option value="">Type d'événement…</option>
            <optgroup label="Positif">
              {kinds.filter(k => k.polarity === 'positif').map(k => <option key={k.kind} value={k.kind}>{k.label}</option>)}
            </optgroup>
            <optgroup label="Négatif">
              {kinds.filter(k => k.polarity === 'negatif').map(k => <option key={k.kind} value={k.kind}>{k.label}</option>)}
            </optgroup>
            <optgroup label="Neutre">
              {kinds.filter(k => k.polarity === 'neutre').map(k => <option key={k.kind} value={k.kind}>{k.label}</option>)}
            </optgroup>
          </select>
          <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
            placeholder="Note (facultatif)" className="border border-gray-200 rounded-lg px-3 py-2 text-sm flex-1" />
          <Button variant="primary" onClick={add} disabled={!form.kind || saving}
            className="gap-1 font-semibold" leftIcon={<Plus size={15} />}>
            Ajouter
          </Button>
        </div>
      )}

      {events.length === 0 ? (
        <p className="text-sm text-gray-400">Aucun événement de relation enregistré.</p>
      ) : (
        <ul className="space-y-2">
          {events.map(e => {
            const ps = _POLARITY[e.polarity ?? 'neutre']
            return (
              <li key={e.id} className="flex items-start gap-2 text-sm">
                <span className="text-xs font-medium px-2 py-0.5 rounded-full shrink-0" style={{ color: ps.color, background: ps.bg }}>{e.kind_label}</span>
                <div className="flex-1 min-w-0">
                  {e.note && <p className="text-gray-800">{e.note}</p>}
                  <p className="text-xs text-gray-400">{e.date}{e.author_name ? ` · ${e.author_name}` : ''}</p>
                </div>
                {canEdit && (
                  <button onClick={() => del(e.id)} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-red-500"><Trash2 size={13} /></button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

// ── Formulaire ajout état des lieux ────────────────────────────────────────────
interface InspectionFormData {
  inspection_type: string
  inspection_date: string
  inspector_name: string
  tenant_present: boolean
  overall_condition: string
  notes: string
}

function InspectionForm({ leaseId, propertyId, onSaved, onCancel }: {
  leaseId: string
  propertyId: string
  onSaved: () => void
  onCancel: () => void
}) {
  const today = format(new Date(), 'yyyy-MM-dd')
  const [form, setForm] = useState<InspectionFormData>({
    inspection_type: 'entree',
    inspection_date: today,
    inspector_name: '',
    tenant_present: true,
    overall_condition: 'bon',
    notes: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (field: keyof InspectionFormData, value: string | boolean) =>
    setForm(f => ({ ...f, [field]: value }))

  const handleSave = async () => {
    setSaving(true); setError('')
    try {
      await inspectionsApi.create({
        lease_id: leaseId,
        property_id: propertyId,
        inspection_type: form.inspection_type,
        inspection_date: form.inspection_date,
        inspector_name: form.inspector_name || undefined,
        tenant_present: form.tenant_present,
        overall_condition: form.overall_condition || undefined,
        notes: form.notes || undefined,
      })
      onSaved()
    } catch (e: any) {
      setError(getErrorMessage(e, 'Erreur lors de la création'))
    } finally {
      setSaving(false)
    }
  }

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const lbl = 'block text-xs font-medium text-gray-700 mb-1'

  return (
    <div className="mt-4 p-4 border border-blue-200 rounded-xl bg-blue-50 space-y-3">
      <p className="text-sm font-semibold text-blue-700">Nouvel état des lieux</p>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className={lbl}>Type</label>
          <select value={form.inspection_type} onChange={e => set('inspection_type', e.target.value)} className={inp}>
            <option value="entree">État des lieux d'entrée</option>
            <option value="sortie">État des lieux de sortie</option>
            <option value="contradictoire">Contradictoire</option>
            <option value="periodique">Visite périodique</option>
          </select>
        </div>
        <div>
          <label className={lbl}>Date</label>
          <input type="date" value={form.inspection_date} onChange={e => set('inspection_date', e.target.value)} className={inp} />
        </div>
        <div>
          <label className={lbl}>Inspecteur</label>
          <input value={form.inspector_name} onChange={e => set('inspector_name', e.target.value)} placeholder="Nom" className={inp} />
        </div>
        <div>
          <label className={lbl}>État général</label>
          <select value={form.overall_condition} onChange={e => set('overall_condition', e.target.value)} className={inp}>
            <option value="tres_bon">Très bon</option>
            <option value="bon">Bon</option>
            <option value="moyen">Moyen</option>
            <option value="mauvais">Mauvais</option>
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input type="checkbox" id="tenant_present" checked={form.tenant_present}
          onChange={e => set('tenant_present', e.target.checked)} className="w-4 h-4 text-blue-600 rounded" />
        <label htmlFor="tenant_present" className="text-sm text-gray-700">Locataire présent</label>
      </div>
      <div>
        <label className={lbl}>Observations</label>
        <textarea value={form.notes} onChange={e => set('notes', e.target.value)} rows={2}
          className={`${inp} resize-none`} placeholder="Remarques générales…" />
      </div>
      <div className="flex gap-2 justify-end">
        <button onClick={onCancel} className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
          Annuler
        </button>
        <button onClick={handleSave} disabled={saving}
          className="px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {saving ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </div>
    </div>
  )
}

const fmtDate = (d?: string | null) =>
  d ? format(new Date(d), 'd MMMM yyyy', { locale: fr }) : ''
const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €'

const REVISION_SOURCE_LABELS: Record<string, string> = {
  manuel: 'Modification du contrat',
  irl: 'Révision IRL',
  charges: 'Régularisation des charges',
  amiable: 'Réévaluation amiable',
  initial: 'Montant initial',
}

// ── Évolution du loyer et des charges (révisions datées, par champ) ──────────
const REVISION_KIND_LABELS: Record<string, string> = { rent: 'Loyer HC', charges: 'Charges' }

function RentHistorySection({ leaseId, canEdit }: { leaseId: string; canEdit: boolean }) {
  const [revisions, setRevisions] = useState<RentRevision[]>([])
  const [loaded, setLoaded] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = () => leasesApi.rentRevisions(leaseId)
    .then(r => setRevisions(r.data)).catch(() => {}).finally(() => setLoaded(true))
  useEffect(() => { load() }, [leaseId])

  if (!loaded || revisions.length === 0) return null

  const today = new Date().toLocaleDateString('fr-CA')

  const del = async (rev: RentRevision) => {
    if (!confirm('Supprimer cette réévaluation programmée ? Elle ne sera pas appliquée.')) return
    setBusyId(rev.id)
    try {
      await leasesApi.deleteRentRevision(leaseId, rev.id)
      toast.success('Réévaluation supprimée.')
      await load()
    } catch (e: any) {
      toast.error(getErrorMessage(e, 'Suppression impossible'))
    } finally { setBusyId(null) }
  }

  // Une révision « courante » par champ (loyer puis charges) : précédent → nouveau.
  const order = ['rent', 'charges'] as const
  const shown = order
    .map(k => revisions.find(r => r.kind === k))
    .filter((r): r is RentRevision => !!r)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 md:col-span-2">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-4">
        <TrendingUp size={15} className="text-blue-500" /> Évolution du loyer et des charges
      </h2>
      <div className="space-y-2">
        {shown.map(r => {
          const isFuture = r.effective_date > today
          return (
            <div key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-gray-200 px-3 py-2.5">
              <span className="text-sm font-semibold text-gray-800 w-20 shrink-0">{REVISION_KIND_LABELS[r.kind] ?? r.kind}</span>
              <span className="text-sm text-gray-400 line-through">{r.prev_amount == null ? '—' : fmtEuro(r.prev_amount)}</span>
              <ArrowRight size={13} className="text-gray-400 shrink-0" />
              <span className="text-sm font-semibold text-gray-900">{fmtEuro(r.amount)}</span>
              <span className="text-xs text-gray-500">à compter du {format(new Date(r.effective_date), 'd MMM yyyy', { locale: fr })}</span>
              <span className="text-xs text-gray-400">· {r.reason || REVISION_SOURCE_LABELS[r.source] || r.source}</span>
              <span className="ml-auto flex items-center gap-2 shrink-0">
                {isFuture
                  ? <StatusBadge label="Programmée" variant="yellow" />
                  : <StatusBadge label="Appliquée" variant="green" />}
                {isFuture && canEdit && (
                  <button
                    onClick={() => del(r)}
                    disabled={busyId === r.id}
                    title="Supprimer cette réévaluation"
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function LeaseDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [lease, setLease] = useState<Lease | null>(null)
  const [inspections, setInspections] = useState<Inspection[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showEdit, setShowEdit] = useState(false)
  const [showTerminate, setShowTerminate] = useState(false)
  const [isTerminating, setIsTerminating] = useState(false)
  const [showInspectionForm, setShowInspectionForm] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  // Revalorisation rapide loyer/charges depuis le contrat (sans passer par Modifier).
  const [reval, setReval] = useState<null | 'rent' | 'charges'>(null)
  const [revalAmount, setRevalAmount] = useState('')
  const [revalEff, setRevalEff] = useState('')
  const [revalBusy, setRevalBusy] = useState(false)
  const [histKey, setHistKey] = useState(0) // force le rechargement de l'historique

  const firstOfNextMonth = () => {
    const d = new Date()
    const y = d.getMonth() === 11 ? d.getFullYear() + 1 : d.getFullYear()
    const m = d.getMonth() === 11 ? 0 : d.getMonth() + 1
    return new Date(y, m, 1).toLocaleDateString('fr-CA')
  }

  const openReval = (kind: 'rent' | 'charges') => {
    if (!lease) return
    setReval(kind)
    setRevalAmount(String(kind === 'rent' ? lease.rent_amount : lease.charges_amount))
    setRevalEff(firstOfNextMonth())
  }

  const submitReval = async () => {
    if (!lease || !reval) return
    const val = parseFloat(revalAmount.replace(',', '.'))
    if (isNaN(val) || val < 0) { toast.error('Montant invalide'); return }
    setRevalBusy(true)
    try {
      await leasesApi.update(lease.id, reval === 'rent'
        ? { rent_amount: val, rent_effective_date: revalEff }
        : { charges_amount: val, rent_effective_date: revalEff })
      toast.success(`${reval === 'rent' ? 'Loyer' : 'Charges'} : nouvelle valeur programmée.`)
      setReval(null)
      await fetchLease()
      setHistKey(k => k + 1)
    } catch (e: any) {
      toast.error(getErrorMessage(e, 'Erreur lors de la revalorisation'))
    } finally { setRevalBusy(false) }
  }

  const fetchLease = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const [leaseRes, inspRes] = await Promise.all([
        leasesApi.get(id),
        inspectionsApi.list({ lease_id: id }),
      ])
      setLease(leaseRes.data)
      setInspections(inspRes.data.items)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchLease() }, [id])

  const handleTerminate = async () => {
    if (!id) return
    setIsTerminating(true)
    try {
      await leasesApi.terminate(id, {
        end_date: format(new Date(), 'yyyy-MM-dd'),
      })
      fetchLease()
    } finally {
      setIsTerminating(false)
      setShowTerminate(false)
    }
  }

  const handleDownloadPdf = async () => {
    if (!lease || !id || pdfLoading) return
    setPdfLoading(true)
    setDownloadError(null)
    try {
      await leasesApi.downloadPdf(id, docFilename('bail_non_meuble', { tenant: lease.tenant?.full_name, property: lease.parent_property?.name }))
    } catch {
      setDownloadError('Erreur lors de la génération du bail non meublé')
    } finally {
      setPdfLoading(false)
    }
  }

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!lease) return <div className="p-6 text-sm text-red-600">Contrat introuvable</div>

  const InfoRow = ({
    label,
    value,
  }: {
    label: string
    value: React.ReactNode
  }) =>
    value ? (
      <div className="flex justify-between items-start py-2 border-b border-gray-50 last:border-0">
        <span className="text-xs text-gray-500">{label}</span>
        <span className="text-sm font-medium text-gray-900 text-right max-w-[60%] whitespace-pre-line leading-tight">{value}</span>
      </div>
    ) : null

  return (
    <div className="p-4 sm:p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/leases')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">
              {lease.tenant?.full_name ?? ''}
            </h1>
            <StatusBadge
              label={lease.is_active ? 'Actif' : 'Résilié'}
              variant={lease.is_active ? 'green' : 'gray'}
              dot
            />
          </div>
          <p className="text-sm text-gray-500">
            {lease.parent_property?.name}
            &nbsp;·&nbsp;{LEASE_TYPE_LABELS[lease.lease_type]}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleDownloadPdf}
            disabled={pdfLoading}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <FileDown size={15} /> {pdfLoading ? 'Génération…' : 'Bail non meublé'}
          </button>
          {lease.is_active && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate(`/sorties?lease=${lease.id}`)}
              className="px-3 py-2 text-sm"
              leftIcon={<DoorOpen size={15} />}
              title="Préavis, état des lieux de sortie, dépôt de garantie, clôture"
            >
              Organiser la sortie
            </Button>
          )}
          {lease.is_active && (
            <button
              onClick={() => setShowTerminate(true)}
              className="flex items-center gap-2 px-3 py-2 border border-red-300 text-sm text-red-600 rounded-lg hover:bg-red-50"
            >
              <XCircle size={15} /> Résilier
            </button>
          )}
          <button
            onClick={() => setShowEdit(true)}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <Edit size={15} /> Modifier
          </button>
        </div>
      </div>

      {downloadError && (
        <div className="mb-4 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {downloadError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Contrat */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
            <Calendar size={15} className="text-blue-500" /> Contrat
          </h2>
          <InfoRow label="Type de bail" value={LEASE_TYPE_LABELS[lease.lease_type]} />
          <InfoRow label="Date d'entrée" value={fmtDate(lease.start_date)} />
          <InfoRow label="Date de fin" value={fmtDate(lease.end_date)} />
          <InfoRow label="Congé donné le" value={fmtDate(lease.notice_date)} />
        </div>

        {/* Bien */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
            <Home size={15} className="text-blue-500" /> Bien immobilier
          </h2>
          <InfoRow label="Bien" value={lease.parent_property?.name} />
          <InfoRow label="Adresse" value={lease.parent_property?.full_address} />
        </div>

        {/* Finances */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
            <CreditCard size={15} className="text-blue-500" /> Finances
          </h2>
          <InfoRow label="Loyer HC" value={
            <span className="inline-flex items-center gap-2">
              {fmtEuro(lease.rent_amount)}
              {lease.is_active && (
                <button onClick={() => openReval('rent')} title="Revaloriser le loyer (programmé)"
                  className="p-1 rounded hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition-colors">
                  <TrendingUp size={13} />
                </button>
              )}
            </span>
          } />
          <InfoRow label="Charges" value={
            <span className="inline-flex items-center gap-2">
              {fmtEuro(lease.charges_amount)}
              {lease.is_active && (
                <button onClick={() => openReval('charges')} title="Revaloriser les charges (programmé)"
                  className="p-1 rounded hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition-colors">
                  <TrendingUp size={13} />
                </button>
              )}
            </span>
          } />
          <InfoRow label="Total CC" value={
            <span className="font-bold text-blue-700">{fmtEuro(lease.total_monthly)}</span>
          } />
          <InfoRow label="Dépôt de garantie" value={fmtEuro(lease.deposit_amount)} />
          <InfoRow label="Paiement le" value={`${lease.payment_day} du mois`} />
          <InfoRow label="Fréquence de paiement" value={PAYMENT_FREQUENCY_LABELS[lease.payment_frequency]} />
          <InfoRow label="Règle d'appel" value={RENT_CALL_RULE_LABELS[lease.rent_call_rule]} />
          {lease.apl_tiers_payant && lease.apl_amount && (
            <>
              <InfoRow label="Aide personnelle au logement" value={
                <span className="text-green-700">- {fmtEuro(lease.apl_amount)}</span>
              } />
              <InfoRow label="Reste à payer (locataire)" value={
                <span className="font-bold text-green-700">{fmtEuro(lease.net_rent + lease.charges_amount)}</span>
              } />
            </>
          )}
        </div>

        {/* Locataire */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
            <User size={15} className="text-blue-500" /> Locataire
          </h2>
          <InfoRow label={lease.co_tenants && lease.co_tenants.length > 0 ? 'Locataire principal' : 'Nom et prénom'} value={lease.tenant?.full_name} />
          <InfoRow label="Email" value={lease.tenant?.email} />
          <InfoRow label="Numéro de sécurité sociale" value={lease.tenant?.national_id ? formatNir(lease.tenant.national_id) : lease.tenant?.national_id} />
          <InfoRow label="Téléphone" value={formatPhoneDisplay(lease.tenant?.phone)} />
          {lease.co_tenants && lease.co_tenants.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-500 mb-1.5">Co-titulaires (solidaires)</p>
              <div className="space-y-1">
                {lease.co_tenants.map(ct => (
                  <p key={ct.id} className="text-sm text-gray-800">
                    {ct.full_name}{ct.email ? <span className="text-gray-400"> : {ct.email}</span> : null}
                  </p>
                ))}
              </div>
            </div>
          )}
          {lease.has_guarantor && (
            <>
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="flex items-center gap-1 text-xs font-semibold text-gray-500 mb-2">
                  <ShieldCheck size={13} /> Garant
                </div>
                <InfoRow label="Nom" value={lease.guarantor_name} />
                <InfoRow label="Email" value={lease.guarantor_email} />
                <InfoRow label="Téléphone" value={formatPhoneDisplay(lease.guarantor_phone)} />
              </div>
            </>
          )}
        </div>

        {/* Notes */}
        {lease.notes && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
              <StickyNote size={15} className="text-blue-500" /> Notes
            </h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{lease.notes}</p>
          </div>
        )}

        {/* Évolution du loyer et des charges (révisions datées) */}
        <RentHistorySection key={histKey} leaseId={lease.id} canEdit={lease.is_active} />

        {/* Relation locataire (scoring) */}
        <RelationSection leaseId={lease.id} canEdit={lease.is_active} />

        {/* États des lieux */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 md:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <ClipboardList size={15} className="text-blue-500" /> États des lieux
            </h2>
            {lease.is_active && !showInspectionForm && (
              <button
                onClick={() => setShowInspectionForm(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <Plus size={13} /> Ajouter
              </button>
            )}
          </div>

          {showInspectionForm && lease && (
            <InspectionForm
              leaseId={lease.id}
              propertyId={lease.property_id}
              onSaved={() => { setShowInspectionForm(false); fetchLease() }}
              onCancel={() => setShowInspectionForm(false)}
            />
          )}

          {!showInspectionForm && inspections.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">Aucun état des lieux enregistré</p>
          )}
          {inspections.length > 0 && (
            <div className="space-y-2 mt-2">
              {inspections.map(insp => (
                <div
                  key={insp.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <span className="text-sm font-medium text-gray-900">
                      {INSPECTION_TYPE_LABELS[insp.inspection_type]}
                    </span>
                    <span className="text-xs text-gray-500 ml-2">
                      {fmtDate(insp.inspection_date)}
                    </span>
                    {insp.inspector_name && (
                      <span className="text-xs text-gray-400 ml-2">— {insp.inspector_name}</span>
                    )}
                    {insp.notes && (
                      <p className="text-xs text-gray-500 mt-0.5 ml-1">{insp.notes}</p>
                    )}
                  </div>
                  {insp.overall_condition && (
                    <StatusBadge
                      label={CONDITION_LABELS[insp.overall_condition]}
                      variant={CONDITION_VARIANTS[insp.overall_condition]}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modale édition */}
      {showEdit && (
        <LeaseForm
          lease={lease}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); fetchLease() }}
        />
      )}

      {/* Confirmation résiliation */}
      <ConfirmDialog
        isOpen={showTerminate}
        onClose={() => setShowTerminate(false)}
        onConfirm={handleTerminate}
        title="Résilier le contrat"
        message="Le logement sera marqué disponible. Cette action est irréversible. Confirmez-vous la résiliation ?"
        isLoading={isTerminating}
        confirmLabel="Résilier"
        confirmVariant="red"
      />

      {/* Revalorisation rapide loyer / charges (révision datée, sans passer par Modifier) */}
      {reval && lease && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 space-y-4">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <TrendingUp size={15} className="text-blue-600" />
              Revaloriser {reval === 'rent' ? 'le loyer (HC)' : 'les charges'}
            </h3>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Nouveau montant (€) — actuel {fmtEuro(reval === 'rent' ? lease.rent_amount : lease.charges_amount)}
              </label>
              <input
                type="number" step="0.01" min="0" autoFocus
                value={revalAmount}
                onChange={e => setRevalAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Date d'effet</label>
              <input
                type="date"
                value={revalEff}
                onChange={e => setRevalEff(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Le mois en cours n'est pas modifié ; la nouvelle valeur s'applique à partir de cette date
                (par défaut le 1er du mois suivant). L'ancien montant est conservé dans l'historique.
              </p>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={() => setReval(null)} disabled={revalBusy}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50">
                Annuler
              </button>
              <button onClick={submitReval} disabled={revalBusy}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-60">
                {revalBusy ? 'Enregistrement…' : 'Programmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
