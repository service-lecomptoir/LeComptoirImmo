import { useState, useEffect } from 'react'
import { CreditCard, TrendingUp } from 'lucide-react'
import { paymentsApi } from '@/api/payments'
import { StatusBadge } from '@/components/common/StatusBadge'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

function paymentStatusVariant(s: string): any {
  const map: Record<string, string> = {
    paid: 'green', partial: 'yellow', pending: 'blue', late: 'red', cancelled: 'gray',
  }
  return map[s] ?? 'gray'
}
function paymentStatusLabel(s: string): string {
  const map: Record<string, string> = {
    paid: 'Payé', partial: 'Partiel', pending: 'En attente', late: 'En retard', cancelled: 'Annulé',
  }
  return map[s] ?? s
}

export default function ProprietaireRevenus() {
  const [payments, setPayments] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    paymentsApi.list({ limit: 50 })
      .then(r => setPayments(r.data.items ?? r.data))
      .catch(() => { })
      .finally(() => setIsLoading(false))
  }, [])

  const totalPercu = payments
    .filter(p => p.status === 'paid' || p.status === 'partial')
    .reduce((s, p) => s + (p.amount_paid ?? 0), 0)

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes revenus</h1>
        <p className="text-gray-500 text-sm mt-1">Historique des paiements sur vos biens</p>
      </div>

      {/* Récap */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 bg-green-50 rounded-xl flex items-center justify-center">
              <CreditCard size={18} className="text-green-600" />
            </div>
            <p className="text-sm text-gray-500">Total perçu (affiché)</p>
          </div>
          <p className="text-2xl font-bold text-gray-900">{fmtEuro(totalPercu)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 bg-blue-50 rounded-xl flex items-center justify-center">
              <TrendingUp size={18} className="text-blue-600" />
            </div>
            <p className="text-sm text-gray-500">Paiements listés</p>
          </div>
          <p className="text-2xl font-bold text-gray-900">{payments.length}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-gray-400 text-sm">Chargement…</div>
        ) : payments.length === 0 ? (
          <div className="py-16 text-center text-gray-400">
            <CreditCard size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucun paiement enregistré</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[640px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Période</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Locataire</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Dû</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Perçu</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {payments.map((p: any) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="text-sm text-gray-900">{p.period_label}</p>
                    {p.payment_date && (
                      <p className="text-xs text-gray-400">
                        {format(new Date(p.payment_date), 'd MMM yyyy', { locale: fr })}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-gray-900">{p.tenant_full_name ?? ''}</p>
                    <p className="text-xs text-gray-400">{p.property_name ?? ''}</p>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-700">{fmtEuro(p.amount_due)}</td>
                  <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">{fmtEuro(p.amount_paid ?? 0)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge label={paymentStatusLabel(p.status)} variant={paymentStatusVariant(p.status)} dot />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  )
}
