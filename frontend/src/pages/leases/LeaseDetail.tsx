import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Edit, FileDown, XCircle,
  Home, User, Calendar, CreditCard, ShieldCheck, StickyNote, ClipboardList
} from 'lucide-react'
import { leasesApi } from '@/api/leases'
import { inspectionsApi } from '@/api/inspections'
import { lettersApi } from '@/api/payments'
import { StatusBadge } from '@/components/common/StatusBadge'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { LeaseForm } from './LeaseForm'
import { LEASE_TYPE_LABELS, PAYMENT_METHOD_LABELS } from '@/types/lease'
import {
  INSPECTION_TYPE_LABELS,
  CONDITION_LABELS,
  CONDITION_VARIANTS,
} from '@/types/inspection'
import type { Lease } from '@/types/lease'
import type { Inspection } from '@/types/inspection'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtDate = (d?: string | null) =>
  d ? format(new Date(d), 'd MMMM yyyy', { locale: fr }) : '—'
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

  const handleDownloadPdf = () => {
    if (!lease || !id) return
    const name = lease.tenant?.full_name.replace(/ /g, '_') ?? id
    leasesApi.downloadPdf(id, `bail_${name}_${lease.start_date}.pdf`)
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
              {lease.tenant?.full_name ?? '—'}
            </h1>
            <StatusBadge
              label={lease.is_active ? 'Actif' : 'Résilié'}
              variant={lease.is_active ? 'green' : 'gray'}
              dot
            />
          </div>
          <p className="text-sm text-gray-500">
            {lease.parent_property?.name} — {lease.unit?.unit_ref}
            &nbsp;·&nbsp;{LEASE_TYPE_LABELS[lease.lease_type]}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleDownloadPdf}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <FileDown size={15} /> PDF bail
          </button>
          <button
            onClick={() => {
              if (!id || !lease) return
              const name = lease.tenant?.full_name.replace(/ /g, '_') ?? id
              lettersApi.downloadAttestationCaf(id, `attestation_caf_${name}_${new Date().getFullYear()}.pdf`)
            }}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <FileDown size={15} /> Attestation CAF
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

        {/* Logement */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
            <Home size={15} className="text-blue-500" /> Logement
          </h2>
          <InfoRow label="Bien" value={lease.parent_property?.name} />
          <InfoRow label="Adresse" value={lease.parent_property?.full_address} />
          <InfoRow label="Logement" value={lease.unit?.unit_ref} />
          <InfoRow label="Type" value={lease.unit?.unit_type} />
          {lease.unit?.area_sqm && (
            <InfoRow label="Surface" value={`${lease.unit.area_sqm} m²`} />
          )}
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
          <InfoRow label="Mode" value={PAYMENT_METHOD_LABELS[lease.payment_method]} />
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
          <InfoRow label="Nom" value={lease.tenant?.full_name} />
          <InfoRow label="Email" value={lease.tenant?.email} />
          <InfoRow label="Téléphone" value={lease.tenant?.phone} />
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
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-4">
            <ClipboardList size={15} className="text-blue-500" /> États des lieux
          </h2>
          {inspections.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">Aucun état des lieux enregistré</p>
          ) : (
            <div className="space-y-2">
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
