import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, FileText, Filter, Building2, Download } from 'lucide-react'
import { Button } from '@/components/ui'
import { leasesApi } from '@/api/leases'
import { LeaseForm } from './LeaseForm'
import { StatusBadge } from '@/components/common/StatusBadge'
import { CardGridSkeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { toast } from '@/store/toast'
import { exportCsv } from '@/utils/exportCsv'
import { LEASE_TYPE_LABELS } from '@/types/lease'
import type { LeaseListItem } from '@/types/lease'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { useAuthStore } from '@/store/authStore'
import { ViewToggle } from '@/components/common/ViewToggle'
import { useViewMode } from '@/hooks/useViewMode'

export default function LeaseList() {
  const navigate = useNavigate()
  const [leases, setLeases] = useState<LeaseListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [filterActive, setFilterActive] = useState<boolean | undefined>(true)
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const user = useAuthStore(s => s.user)
  const canToggleView = ['gestionnaire', 'gestionnaire_proprio', 'proprietaire'].includes(user?.role ?? '')
  const [view, setView] = useViewMode('leases', 'grid')
  const [limit, setLimit] = useState(100)

  const fetchLeases = useCallback(async (q: string, active: boolean | undefined, lim: number) => {
    setIsLoading(true)
    try {
      const { data } = await leasesApi.list({
        search: q || undefined,
        is_active: active,
        limit: lim,
      })
      setLeases(data.items)
      setTotal(data.total)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchLeases(search, filterActive, limit), 300)
    return () => clearTimeout(t)
  }, [search, filterActive, limit, fetchLeases])

  const fmtDate = (d: string) => format(new Date(d), 'd MMM yyyy', { locale: fr })
  const fmtEuro = (n: number) => n.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €'

  const handleExport = () => {
    exportCsv('contrats',
      ['Locataire', 'Bien', 'Type', 'Début', 'Loyer', 'Charges', 'Loyer CC', 'Statut'],
      leases.map(l => [
        l.tenant_full_name, l.property_name,
        LEASE_TYPE_LABELS[l.lease_type],
        fmtDate(l.start_date),
        l.rent_amount, l.charges_amount,
        l.rent_amount + l.charges_amount,
        l.is_active ? 'Actif' : 'Résilié',
      ]))
    toast.success(`${leases.length} contrat(s) exporté(s)`)
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contrats de bail</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} contrat{total > 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          {canToggleView && <ViewToggle value={view} onChange={setView} />}
          <Button
            variant="secondary"
            onClick={handleExport}
            disabled={leases.length === 0}
            leftIcon={<Download size={16} />}
            className="px-3"
          >
            Exporter
          </Button>
          <Button
            onClick={() => setShowForm(true)}
            leftIcon={<Plus size={16} />}
          >
            Nouveau contrat
          </Button>
        </div>
      </div>

      {/* Filtres */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => { setSearch(e.target.value); setLimit(100) }}
            placeholder="Rechercher par locataire, logement, bien..."
            className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <Filter size={14} className="text-gray-400" />
          <select
            value={filterActive === undefined ? '' : String(filterActive)}
            onChange={e => {
              const v = e.target.value
              setFilterActive(v === '' ? undefined : v === 'true')
              setLimit(100)
            }}
            className="outline-none text-gray-700 bg-transparent cursor-pointer"
          >
            <option value="true">Actifs</option>
            <option value="false">Résiliés</option>
            <option value="">Tous</option>
          </select>
        </div>
      </div>

      {/* Liste ou mosaïque */}
      {isLoading && leases.length === 0 ? (
        <CardGridSkeleton />
      ) : leases.length === 0 ? (
        <EmptyState icon={FileText} title={search ? 'Aucun résultat' : 'Aucun contrat enregistré'} />
      ) : view === 'list' ? (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px]">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Locataire</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Bien</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Type</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Début</th>
                  <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Loyer CC</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Statut</th>
                </tr>
              </thead>
              <tbody>
                {leases.map(lease => (
                  <tr
                    key={lease.id}
                    onClick={() => navigate(`/leases/${lease.id}`)}
                    className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span className="text-sm font-medium text-gray-900">{lease.tenant_full_name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm text-gray-900">{lease.property_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-600">{LEASE_TYPE_LABELS[lease.lease_type]}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">{fmtDate(lease.start_date)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm font-semibold text-gray-900">
                        {fmtEuro(lease.rent_amount + lease.charges_amount)}
                      </span>
                      {lease.apl_tiers_payant && (
                        <div className="text-xs text-green-600">Tiers-payant CAF</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge
                        label={lease.is_active ? 'Actif' : 'Résilié'}
                        variant={lease.is_active ? 'green' : 'gray'}
                        dot
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {leases.map(lease => (
            <div
              key={lease.id}
              onClick={() => navigate(`/leases/${lease.id}`)}
              className="group flex flex-col gap-3 bg-white rounded-xl border border-gray-200 shadow-sm p-4 cursor-pointer transition-all hover:shadow-md hover:border-blue-300"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-gray-600">{LEASE_TYPE_LABELS[lease.lease_type]}</span>
                <StatusBadge
                  label={lease.is_active ? 'Actif' : 'Résilié'}
                  variant={lease.is_active ? 'green' : 'gray'}
                  dot
                />
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                  <FileText size={18} className="text-blue-600" />
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-gray-900 truncate">{lease.tenant_full_name}</p>
                  <p className="text-xs text-gray-500 truncate flex items-center gap-1">
                    <Building2 size={12} className="shrink-0" />
                    {lease.property_name}
                  </p>
                </div>
              </div>

              <div className="mt-auto flex items-end justify-between gap-2 pt-2 border-t border-gray-100">
                <span className="text-xs text-gray-500">Début {fmtDate(lease.start_date)}</span>
                <div className="text-right">
                  <span className="text-sm font-semibold text-gray-900">
                    {fmtEuro(lease.rent_amount + lease.charges_amount)}
                  </span>
                  {lease.apl_tiers_payant && (
                    <div className="text-xs text-green-600">Tiers-payant CAF</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && leases.length < total && leases.length < 1000 && (
        <div className="flex justify-center mt-4">
          <Button
            variant="secondary"
            onClick={() => setLimit(l => Math.min(l + 100, 1000))}
          >
            Charger plus ({leases.length} / {total})
          </Button>
        </div>
      )}

      {showForm && (
        <LeaseForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchLeases(search, filterActive, limit); toast.success('Contrat enregistré') }}
        />
      )}
    </div>
  )
}
