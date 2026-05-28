import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Edit, FileDown, XCircle,
  Home, User, Calendar, CreditCard, ShieldCheck, StickyNote, ClipboardList, Plus,
} from 'lucide-react'
import { leasesApi } from '@/api/leases'
import { inspectionsApi } from '@/api/inspections'
import { lettersApi } from '@/api/payments'
import { StatusBadge } from '@/components/common/StatusBadge'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { LeaseForm } from './LeaseForm'
import { LEASE_TYPE_LABELS, RENT_CALL_RULE_LABELS } from '@/types/lease'
import {
  INSPECTION_TYPE_LABELS,
  CONDITION_LABELS,
  CONDITION_VARIANTS,
} from '@/types/inspection'
import type { Lease } from '@/types/lease'
import type { Inspection } from '@/types/inspection'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

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
      setError(e?.response?.data?.detail || 'Erreur lors de la création')
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
      <div className="grid grid-cols-2 gap-3">
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
  const [cafLoading, setCafLoading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

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
      const name = lease.tenant?.full_name.replace(/ /g, '_') ?? id
      await leasesApi.downloadPdf(id, `bail_${name}_${lease.start_date}.pdf`)
    } catch {
      setDownloadError('Erreur lors de la génération du PDF bail')
    } finally {
      setPdfLoading(false)
    }
  }

  const handleDownloadCaf = async () => {
    if (!id || !lease || cafLoading) return
    setCafLoading(true)
    setDownloadError(null)
    try {
      const name = lease.tenant?.full_name.replace(/ /g, '_') ?? id
      await lettersApi.downloadAttestationCaf(id, `attestation_caf_${name}_${new Date().getFullYear()}.pdf`)
    } catch {
      setDownloadError("Erreur lors de la génération de l'attestation CAF")
    } finally {
      setCafLoading(false)
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
        <span className="text-sm font-medium text-gray-900 text-right max-w-[60%]">{value}</span>
      </div>
    ) : null

  return (
    <div className="p-6 max-w-5xl">
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
            <FileDown size={15} /> {pdfLoading ? 'Génération…' : 'PDF bail'}
          </button>
          <button
            onClick={handleDownloadCaf}
            disabled={cafLoading}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <FileDown size={15} /> {cafLoading ? 'Génération…' : 'Attestation CAF'}
          </button>
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
          <InfoRow label="Loyer HC" value={fmtEuro(lease.rent_amount)} />
          <InfoRow label="Charges" value={fmtEuro(lease.charges_amount)} />
          <InfoRow label="Total CC" value={
            <span className="font-bold text-blue-700">{fmtEuro(lease.total_monthly)}</span>
          } />
          <InfoRow label="Dépôt de garantie" value={fmtEuro(lease.deposit_amount)} />
          <InfoRow label="Paiement le" value={`${lease.payment_day} du mois`} />
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
          <InfoRow label={lease.co_tenants && lease.co_tenants.length > 0 ? 'Locataire principal' : 'Nom'} value={lease.tenant?.full_name} />
          <InfoRow label="Email" value={lease.tenant?.email} />
          <InfoRow label="Téléphone" value={lease.tenant?.phone} />
          {lease.co_tenants && lease.co_tenants.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-500 mb-1.5">Co-titulaires (solidaires)</p>
              <div className="space-y-1">
                {lease.co_tenants.map(ct => (
                  <p key={ct.id} className="text-sm text-gray-800">
                    {ct.full_name}{ct.email ? <span className="text-gray-400"> — {ct.email}</span> : null}
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
                <InfoRow label="Téléphone" value={lease.guarantor_phone} />
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
    </div>
  )
}
