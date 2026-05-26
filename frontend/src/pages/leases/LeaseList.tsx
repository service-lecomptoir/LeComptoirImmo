import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, FileText, Filter } from 'lucide-react'
import { leasesApi } from '@/api/leases'
import { LeaseForm } from './LeaseForm'
import { StatusBadge } from '@/components/common/StatusBadge'
import { LEASE_TYPE_LABELS } from '@/types/lease'
import type { LeaseListItem } from '@/types/lease'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

export default function LeaseList() {
  const navigate = useNavigate()
  const [leases, setLeases] = useState<LeaseListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [filterActive, setFilterActive] = useState<boolean | undefined>(true)
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  const fetchLeases = useCallback(async (q: string, active: boolean | undefined) => {
    setIsLoading(true)
    try {
      const { data } = await leasesApi.list({
        search: q || undefined,
        is_active: active,
        limit: 100,
      })
      setLeases(data.items)
      setTotal(data.total)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchLeases(search, filterActive), 300)
    return () => clearTimeout(t)
  }, [search, filterActive, fetchLeases])

  const fmtDate = (d: string) => format(new Date(d), 'd MMM yyyy', { locale: fr })
  const fmtEuro = (n: number) => n.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €'

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contrats de bail</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} contrat{total > 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} /> Nouveau contrat
        </button>
      </div>

      {/* Filtres */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
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
            }}
            className="outline-none text-gray-700 bg-transparent cursor-pointer"
          >
            <option value="true">Actifs</option>
            <option value="false">Résiliés</option>
            <option value="">Tous</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Locataire</th>
              <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Bien / Logement</th>
              <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Type</th>
              <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Début</th>
              <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Loyer CC</th>
              <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Statut</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-sm text-gray-500">Chargement...</td>
              </tr>
            ) : leases.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                    <FileText size={32} className="text-gray-300 mb-2" />
                    <p className="text-sm">{search ? 'Aucun résultat' : 'Aucun contrat enregistré'}</p>
                  </div>
                </td>
              </tr>
            ) : (
              leases.map(lease => (
                <tr
                  key={lease.id}
                  onClick={() => navigate(`/leases/${lease.id}`)}
                  className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-xs font-bold text-blue-700 flex-shrink-0">
                        {lease.tenant_full_name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium text-gray-900">{lease.tenant_full_name}</span>
                    </div>
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
              ))
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <LeaseForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchLeases(search, filterActive) }}
        />
      )}
    </div>
  )
}
