import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ClipboardCheck, DoorOpen, LogIn, Plus } from 'lucide-react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { leasesApi } from '@/api/leases'
import { inspectionsApi } from '@/api/inspections'
import { StatusBadge } from '@/components/common/StatusBadge'
import { InspectionForm } from '@/components/inspections/InspectionForm'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import type { LeaseListItem } from '@/types/lease'
import type { Inspection } from '@/types/inspection'
import {
  CONDITION_LABELS,
  CONDITION_VARIANTS,
  INSPECTION_TYPE_LABELS,
} from '@/types/inspection'
import SortiesPage from '@/pages/sorties/SortiesPage'

const fmtDate = (d?: string | null) =>
  d ? format(new Date(d), 'd MMMM yyyy', { locale: fr }) : ''

type TabKey = 'arrivee' | 'depart'

// ── Onglet Arrivée : états des lieux d'ENTRÉE (par bail) ───────────────────────
function ArriveeTab() {
  const [leases, setLeases] = useState<LeaseListItem[]>([])
  const [leaseId, setLeaseId] = useState('')
  const [inspections, setInspections] = useState<Inspection[]>([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    leasesApi
      .list({ is_active: true, limit: 200 })
      .then(r => setLeases(r.data.items ?? []))
      .catch(() => setLeases([]))
  }, [])

  const selectedLease = useMemo(
    () => leases.find(l => l.id === leaseId) || null,
    [leases, leaseId],
  )

  const loadInspections = async (lid: string) => {
    if (!lid) {
      setInspections([])
      return
    }
    setLoading(true)
    try {
      const r = await inspectionsApi.list({ lease_id: lid })
      setInspections((r.data.items ?? []).filter(i => i.inspection_type === 'entree'))
    } catch (e: any) {
      toast.error(getErrorMessage(e, "Chargement des états des lieux impossible"))
      setInspections([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setShowForm(false)
    loadInspections(leaseId)
  }, [leaseId])

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        États des lieux <strong>d'entrée</strong> : sélectionnez un bail pour consulter
        ou ajouter l'état des lieux d'arrivée du locataire.
      </p>

      <div className="max-w-xl">
        <label className="block text-xs font-medium text-gray-700 mb-1">Bail</label>
        <select
          value={leaseId}
          onChange={e => setLeaseId(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">— Choisir un bail —</option>
          {leases.map(l => (
            <option key={l.id} value={l.id}>
              {l.tenant_full_name} — {l.property_name}
            </option>
          ))}
        </select>
      </div>

      {selectedLease && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <LogIn size={15} className="text-blue-500" /> États des lieux d'entrée —{' '}
              {selectedLease.property_name}
            </h2>
            {!showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100"
              >
                <Plus size={13} /> Ajouter
              </button>
            )}
          </div>

          {showForm && (
            <InspectionForm
              leaseId={selectedLease.id}
              propertyId={selectedLease.property_id}
              lockedType="entree"
              onSaved={() => {
                setShowForm(false)
                loadInspections(selectedLease.id)
                toast.success("État des lieux d'entrée enregistré.")
              }}
              onCancel={() => setShowForm(false)}
            />
          )}

          {!showForm && loading && (
            <p className="text-sm text-gray-400 text-center py-4">Chargement…</p>
          )}
          {!showForm && !loading && inspections.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">
              Aucun état des lieux d'entrée pour ce bail.
            </p>
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
      )}
    </div>
  )
}

/**
 * Page « État des lieux » : regroupe l'Arrivée (états des lieux d'entrée) et le
 * Départ (processus de sortie complet : préavis, état des lieux de sortie,
 * comparaison, décompte du dépôt de garantie, clôture).
 */
export default function EtatsDesLieuxPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab: TabKey = searchParams.get('tab') === 'depart' ? 'depart' : 'arrivee'

  const setTab = (t: TabKey) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', t)
    setSearchParams(next, { replace: true })
  }

  const tabBtn = (t: TabKey, label: string, Icon: typeof LogIn) => (
    <button
      onClick={() => setTab(t)}
      className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
        tab === t
          ? 'border-blue-600 text-blue-700'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      <Icon size={16} /> {label}
    </button>
  )

  return (
    <div className="max-w-5xl mx-auto p-4 sm:p-6">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-4">
        <ClipboardCheck size={22} /> État des lieux
      </h1>

      <div className="flex items-center gap-1 border-b border-gray-200 mb-5">
        {tabBtn('arrivee', 'Arrivée', LogIn)}
        {tabBtn('depart', 'Départ', DoorOpen)}
      </div>

      {tab === 'arrivee' ? <ArriveeTab /> : <SortiesPage embedded />}
    </div>
  )
}
