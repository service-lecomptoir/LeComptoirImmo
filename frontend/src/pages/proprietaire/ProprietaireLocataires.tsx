import { useState, useEffect } from 'react'
import { Users, Home } from 'lucide-react'
import { leasesApi } from '@/api/leases'

export default function ProprietaireLocataires() {
  const [leases, setLeases] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    leasesApi.list({ is_active: true, limit: 100 })
      .then(r => setLeases(r.data.items ?? r.data))
      .catch(() => { })
      .finally(() => setIsLoading(false))
  }, [])

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes locataires</h1>
        <p className="text-gray-500 text-sm mt-1">Locataires en cours sur vos biens</p>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400 text-sm">Chargement…</div>
      ) : leases.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400">
          <Users size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Aucun locataire actif</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Locataire</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Logement</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Loyer CC</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Depuis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {leases.map((l: any) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{l.tenant_full_name}</p>
                    <p className="text-xs text-gray-400">Bail {l.lease_type}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <Home size={13} className="text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-700">{l.property_name}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <p className="text-sm font-semibold text-gray-900">
                      {(l.rent_amount + l.charges_amount).toLocaleString('fr-FR', { minimumFractionDigits: 0 })} €
                    </p>
                    {l.apl_tiers_payant && (
                      <p className="text-xs text-green-600">Aide personnelle au logement (tiers-payant)</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-gray-700">
                      {l.start_date ? new Date(l.start_date).toLocaleDateString('fr-FR') : ''}
                    </p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
