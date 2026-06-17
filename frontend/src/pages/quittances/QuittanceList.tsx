import { useState, useEffect, useCallback } from 'react'
import { Receipt, Search, FileDown, RefreshCw } from 'lucide-react'
import { paymentsApi } from '@/api/payments'
import { docFilename } from '@/utils/filename'
import { formatEuro } from '@/utils/format'
import type { PaymentListItem } from '@/types/payment'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const MONTHS = [
  '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

export default function QuittanceList() {
  const today = new Date()
  const [payments, setPayments] = useState<PaymentListItem[]>([])
  const [_total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [filterYear, setFilterYear] = useState(today.getFullYear())
  const [filterMonth, setFilterMonth] = useState(today.getMonth() + 1)
  const [isLoading, setIsLoading] = useState(true)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  const fetchPayments = useCallback(
    async (q: string, year: number, month: number) => {
      setIsLoading(true)
      try {
        const { data } = await paymentsApi.list({
          search: q || undefined,
          year,
          month,
          limit: 200,
        })
        // Règle : quittance uniquement pour un loyer INTÉGRALEMENT payé.
        setPayments(data.items.filter(p => p.status === 'paid'))
        setTotal(data.total)
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  useEffect(() => {
    const t = setTimeout(
      () => fetchPayments(search, filterYear, filterMonth),
      300
    )
    return () => clearTimeout(t)
  }, [search, filterYear, filterMonth, fetchPayments])

  const handleDownload = async (p: PaymentListItem) => {
    setDownloadingId(p.id)
    try {
      await paymentsApi.downloadQuittance(
        p.id,
        docFilename('quittance', { tenant: p.tenant_full_name, property: p.property_name, month: p.period_month, year: p.period_year })
      )
      fetchPayments(search, filterYear, filterMonth)
    } finally {
      setDownloadingId(null)
    }
  }

  const fmtEuro = formatEuro
  const generatedCount = payments.filter(p => p.quittance_generated_at).length

  return (
    <div className="p-4 sm:p-6">
      {/* En-tête */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Quittances de loyer</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {payments.length} quittance{payments.length > 1 ? 's' : ''} disponible{payments.length > 1 ? 's' : ''} au téléchargement.
        </p>
      </div>

      {/* Stats rapides */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide font-semibold mb-1">Total quittances</p>
          <p className="text-2xl font-bold text-gray-900">{payments.length}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide font-semibold mb-1">Déjà générées</p>
          <p className="text-2xl font-bold text-blue-600">{generatedCount}</p>
        </div>
      </div>

      {/* Filtres */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher un locataire, logement..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={filterMonth}
          onChange={e => setFilterMonth(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
        >
          {MONTHS.slice(1).map((m, i) => (
            <option key={i + 1} value={i + 1}>{m}</option>
          ))}
        </select>
        <select
          value={filterYear}
          onChange={e => setFilterYear(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
        >
          {[today.getFullYear() - 2, today.getFullYear() - 1, today.getFullYear(), today.getFullYear() + 1].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Locataire</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Bien</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Période</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Dû</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Payé</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Quittance</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-sm text-gray-500">
                  <RefreshCw size={18} className="animate-spin inline mr-2" />
                  Chargement...
                </td>
              </tr>
            ) : payments.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                    <Receipt size={36} className="text-gray-300 mb-3" />
                    <p className="text-sm font-medium text-gray-500">Aucune quittance pour cette période</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Les quittances apparaissent automatiquement lorsqu'un loyer est intégralement payé.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              payments.map(p => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">{p.tenant_full_name}</td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-900 whitespace-nowrap">{p.property_name}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">{p.period_label}</td>
                  <td className="px-4 py-3 text-sm text-right text-gray-900 whitespace-nowrap">{fmtEuro(p.amount_due)}</td>
                  <td className="px-4 py-3 text-sm text-right text-green-700 font-medium whitespace-nowrap">
                    {/* Payé effectif = règlement direct + part couverte par un plan
                        d'apurement (cohérent avec la quittance PDF). */}
                    {fmtEuro(p.amount_paid + (p.amount_on_plan || 0))}
                    {(p.amount_on_plan || 0) > 0.005 && (
                      <div className="text-[11px] font-normal text-gray-400">
                        dont {fmtEuro(p.amount_on_plan || 0)} par apurement
                      </div>
                    )}
                  </td>

                  {/* Date de génération de la quittance */}
                  <td className="px-4 py-3 text-xs whitespace-nowrap">
                    {p.quittance_generated_at ? (
                      <span className="text-blue-600 font-medium">
                        {format(new Date(p.quittance_generated_at), 'd MMM yyyy', { locale: fr })}
                      </span>
                    ) : (
                      <span className="text-gray-400">Non générée</span>
                    )}
                  </td>

                  {/* Action : téléchargement uniquement */}
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end">
                      <button
                        onClick={() => handleDownload(p)}
                        disabled={downloadingId === p.id}
                        title="Télécharger la quittance PDF"
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 disabled:opacity-50 transition-colors"
                      >
                        {downloadingId === p.id
                          ? <RefreshCw size={12} className="animate-spin" />
                          : <FileDown size={12} />
                        }
                        Télécharger
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Légende */}
      <p className="text-xs text-gray-400 mt-4">
        Seuls les paiements avec statut <strong>Payé</strong> apparaissent ici.
        L'<strong>envoi</strong> des quittances (e-mail / SMS) est géré automatiquement dans
        <strong> Communication et automatisation</strong>.
      </p>
    </div>
  )
}
