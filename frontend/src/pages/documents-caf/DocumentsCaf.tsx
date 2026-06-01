import { useEffect, useMemo, useState } from 'react'
import { Landmark, Search, FileDown, Loader2 } from 'lucide-react'
import { leasesApi } from '@/api/leases'
import { lettersApi } from '@/api/payments'
import type { LeaseListItem } from '@/types/lease'
import { docFilename } from '@/utils/filename'
import { toast } from '@/store/toast'

export default function DocumentsCaf() {
  const [leases, setLeases] = useState<LeaseListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    leasesApi.list({ is_active: true, limit: 200 })
      .then(r => setLeases(r.data.items ?? []))
      .catch(() => toast.error('Chargement des contrats impossible'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return leases
    return leases.filter(l =>
      l.tenant_full_name?.toLowerCase().includes(q) ||
      l.property_name?.toLowerCase().includes(q)
    )
  }, [leases, search])

  const downloadAttestation = async (lease: LeaseListItem) => {
    setDownloadingId(lease.id)
    try {
      await lettersApi.downloadAttestationCaf(
        lease.id,
        docFilename('attestation_loyer_caf', {
          tenant: lease.tenant_full_name,
          property: lease.property_name,
          year: new Date().getFullYear(),
        }),
      )
    } catch {
      toast.error("Génération de l'attestation impossible")
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
          <Landmark className="text-blue-600" size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents CAF</h1>
          <p className="text-gray-500 text-sm">Génération de l'attestation de loyer (CERFA 10842*07) pour la CAF / MSA</p>
        </div>
      </div>

      <p className="text-sm text-gray-500 mb-6 max-w-2xl">
        Sélectionnez un contrat : l'attestation de loyer est pré-remplie à partir des informations du bailleur,
        du locataire et du bail. Le bailleur n'a plus qu'à la vérifier et la signer.
      </p>

      <div className="relative mb-5 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher par locataire ou bien…"
          className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="animate-spin text-blue-600" size={28} />
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full min-w-[640px]">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Locataire</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Bien</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Depuis le</th>
                <th className="px-6 py-3.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Attestation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-sm text-gray-400">
                    {search ? 'Aucun contrat ne correspond à votre recherche' : 'Aucun contrat actif'}
                  </td>
                </tr>
              ) : (
                filtered.map(l => (
                  <tr key={l.id} className="hover:bg-blue-50/40 transition-colors">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{l.tenant_full_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{l.property_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                      {l.start_date ? new Date(l.start_date).toLocaleDateString('fr-FR') : '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => downloadAttestation(l)}
                        disabled={downloadingId === l.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors disabled:opacity-60"
                      >
                        {downloadingId === l.id ? <Loader2 size={15} className="animate-spin" /> : <FileDown size={15} />}
                        Attestation de loyer
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
