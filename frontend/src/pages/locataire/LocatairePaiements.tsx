import { useState, useEffect } from 'react'
import { CreditCard, Download } from 'lucide-react'
import { paymentsApi } from '@/api/payments'
import { docFilename } from '@/utils/filename'
import { StatusBadge } from '@/components/common/StatusBadge'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

export default function LocatairePaiements() {
  const [payments, setPayments] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    paymentsApi.list({ limit: 36 })
      .then(r => setPayments(r.data.items ?? r.data))
      .catch(() => { })
      .finally(() => setIsLoading(false))
  }, [])

  const totalPaye = payments
    .filter(p => p.status === 'paid' || p.status === 'partial')
    .reduce((s, p) => s + (p.amount_paid ?? 0), 0)

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes paiements</h1>
        <p className="text-gray-500 text-sm mt-1">Historique de vos règlements</p>
      </div>

      {/* Résumé */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center">
            <CreditCard size={18} className="text-green-600" />
          </div>
          <div>
            <p className="text-xs text-gray-500">Total versé (affiché)</p>
            <p className="text-xl font-bold text-gray-900">{fmtEuro(totalPaye)}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
        ) : payments.length === 0 ? (
          <div className="py-12 text-center text-gray-400">
            <CreditCard size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucun paiement enregistré</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[640px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Période</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Dû</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Versé</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Quittance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {payments.map((p: any) => {
                const statusMap: Record<string, { label: string; variant: any }> = {
                  paid: { label: 'Payé', variant: 'green' },
                  partial: { label: 'Partiel', variant: 'yellow' },
                  pending: { label: 'En attente', variant: 'blue' },
                  late: { label: 'En retard', variant: 'red' },
                  cancelled: { label: 'Annulé', variant: 'gray' },
                }
                const { label, variant } = statusMap[p.status] ?? { label: p.status, variant: 'gray' }
                const canDownloadQuittance = p.status === 'paid'
                return (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="text-sm text-gray-900">{p.period_label}</p>
                      {p.payment_date && (
                        <p className="text-xs text-gray-400">
                          {format(new Date(p.payment_date), 'd MMM yyyy', { locale: fr })}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-700">{fmtEuro(p.amount_due)}</td>
                    <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">{fmtEuro(p.amount_paid ?? 0)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge label={label} variant={variant} dot />
                    </td>
                    <td className="px-4 py-3 text-center">
                      {canDownloadQuittance ? (
                        <button
                          onClick={() => paymentsApi.downloadQuittance(
                            p.id,
                            docFilename('quittance', { tenant: p.tenant_full_name, property: p.property_name, month: p.period_month, year: p.period_year })
                          )}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 transition-colors"
                        >
                          <Download size={11} />
                          PDF
                        </button>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  )
}
