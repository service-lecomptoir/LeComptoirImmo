import { useEffect, useState } from 'react'
import { Megaphone, Eye, ExternalLink, Lock } from 'lucide-react'
import { apiClient } from '@/api/client'

interface ListingRow {
  property_id: string
  property_name: string | null
  title: string | null
  status: string
  public_path: string | null
  scheduled_at: string | null
  published_at: string | null
  views_count: number
}

const STATUS: Record<string, { label: string; cls: string }> = {
  published: { label: 'Publiée', cls: 'bg-green-100 text-green-700' },
  scheduled: { label: 'Programmée', cls: 'bg-amber-100 text-amber-700' },
  draft: { label: 'Brouillon', cls: 'bg-gray-100 text-gray-600' },
  unpublished: { label: 'Dépubliée', cls: 'bg-gray-100 text-gray-500' },
}

export default function ProprietaireAnnonces() {
  const [rows, setRows] = useState<ListingRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get<ListingRow[]>('/publishing/listings')
      .then(r => setRows(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const fmtDate = (s: string | null) => (s ? new Date(s).toLocaleDateString('fr-FR') : '—')

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
          <Megaphone className="text-blue-600" size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Annonces de mes biens</h1>
          <p className="text-gray-500 text-sm">Suivi de la mise en location de vos biens.</p>
        </div>
      </div>

      <div className="mb-5 flex items-center gap-2 text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
        <Lock size={13} className="shrink-0" />
        Vue en lecture seule. La publication et la modification des annonces sont gérées par votre gestionnaire.
      </div>

      {loading ? (
        <div className="bg-white rounded-2xl border border-gray-100 px-6 py-12 text-center text-sm text-gray-400">Chargement…</div>
      ) : rows.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 px-6 py-12 text-center text-sm text-gray-400">
          Aucune annonce pour vos biens pour le moment.
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full min-w-[640px]">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Bien</th>
                <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
                <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">Vues</th>
                <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">Publiée le</th>
                <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Annonce</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {rows.map(r => {
                const st = STATUS[r.status] ?? { label: r.status, cls: 'bg-gray-100 text-gray-600' }
                return (
                  <tr key={r.property_id} className="hover:bg-blue-50/40 transition-colors">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {r.property_name || 'Bien'}
                      {r.title && <span className="block text-xs text-gray-400 font-normal truncate max-w-[260px]">{r.title}</span>}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5"><Eye size={13} className="text-gray-400" />{r.views_count}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">{fmtDate(r.published_at)}</td>
                    <td className="px-6 py-4 text-right">
                      {r.public_path ? (
                        <a href={`${window.location.origin}${r.public_path}`} target="_blank" rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium whitespace-nowrap">
                          Voir l'annonce <ExternalLink size={14} />
                        </a>
                      ) : (
                        <span className="text-xs text-gray-300 italic">Non publiée</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
