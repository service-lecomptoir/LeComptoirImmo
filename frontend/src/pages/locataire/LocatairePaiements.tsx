import { useState, useEffect, useCallback } from 'react'
import { CreditCard, Download, CalendarClock, Send } from 'lucide-react'
import { paymentsApi } from '@/api/payments'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { docFilename } from '@/utils/filename'
import { StatusBadge } from '@/components/common/StatusBadge'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

const STATUS_MAP: Record<string, { label: string; variant: any }> = {
  paid: { label: 'Payé', variant: 'green' },
  partial: { label: 'Partiel', variant: 'yellow' },
  pending: { label: 'En attente', variant: 'blue' },
  late: { label: 'En retard', variant: 'red' },
  declared: { label: 'Déclaré (à valider)', variant: 'yellow' },
  cancelled: { label: 'Annulé', variant: 'gray' },
}

interface Row {
  key: string
  label: string
  due: number
  paid: number
  status: string
  date: string | null       // date affichée
  sortDate: string          // pour le tri
  isInstallment: boolean
  planId?: string
  seq?: number
  payment?: any
}

export default function LocatairePaiements() {
  const [payments, setPayments] = useState<any[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [declaring, setDeclaring] = useState<string | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const [pr, pl] = await Promise.allSettled([
        paymentsApi.list({ limit: 60 }),
        apurementApi.mine(),
      ])
      if (pr.status === 'fulfilled') setPayments(pr.value.data.items ?? pr.value.data)
      if (pl.status === 'fulfilled') setPlans(pl.value.data.filter(x => x.status === 'active'))
    } catch { /* ignore */ } finally { setIsLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const declareInst = async (planId: string, seq: number) => {
    setDeclaring(`${planId}-${seq}`)
    try {
      await apurementApi.declareInstallment(planId, seq)
      toast.success('Paiement déclaré : votre gestionnaire le validera à réception.')
      await load()
    } catch (e: any) {
      toast.error(getErrorMessage(e, 'Déclaration impossible'))
    } finally { setDeclaring(null) }
  }

  const today = new Date().toISOString().slice(0, 10)

  // Lignes « loyers » + lignes « échéances d'apurement », unifiées.
  const rows: Row[] = [
    ...payments.map((p: any): Row => ({
      key: `pay-${p.id}`,
      label: p.period_label,
      due: p.amount_due ?? 0,
      paid: p.amount_paid ?? 0,
      status: p.status,
      date: p.payment_date || p.due_date || null,
      sortDate: p.due_date || p.payment_date || '',
      isInstallment: false,
      payment: p,
    })),
    ...plans.flatMap(pl => pl.installments.map((i): Row => ({
      key: `inst-${pl.id}-${i.seq}`,
      label: `Plan d'apurement · échéance ${i.seq}`,
      due: i.amount,
      paid: i.paid ? i.amount : 0,
      status: i.paid ? 'paid' : i.declared ? 'declared' : (i.due_date < today ? 'late' : 'pending'),
      date: i.paid ? (i.paid_date || i.due_date) : i.due_date,
      sortDate: i.due_date,
      isInstallment: true,
      planId: pl.id,
      seq: i.seq,
    }))),
  ]

  const upcoming = rows.filter(r => r.status !== 'paid' && r.status !== 'cancelled')
    .sort((a, b) => a.sortDate.localeCompare(b.sortDate))
  const history = rows.filter(r => r.status === 'paid' || r.status === 'cancelled')
    .sort((a, b) => b.sortDate.localeCompare(a.sortDate))

  const totalPaye = rows.filter(r => r.status === 'paid' || r.status === 'partial')
    .reduce((s, r) => s + r.paid, 0)

  const renderTable = (list: Row[], showDeclare: boolean) => (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px]">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Échéance / Période</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Dû</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Versé</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
            <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {list.map(r => {
            const { label, variant } = STATUS_MAP[r.status] ?? { label: r.status, variant: 'gray' }
            return (
              <tr key={r.key} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <p className="text-sm text-gray-900 flex items-center gap-1.5">
                    {r.isInstallment && <CalendarClock size={13} className="text-amber-500 shrink-0" />}
                    {r.label}
                  </p>
                  {r.date && (
                    <p className="text-xs text-gray-400">{format(new Date(r.date), 'd MMM yyyy', { locale: fr })}</p>
                  )}
                </td>
                <td className="px-4 py-3 text-right text-sm text-gray-700">{fmtEuro(r.due)}</td>
                <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">{fmtEuro(r.paid)}</td>
                <td className="px-4 py-3"><StatusBadge label={label} variant={variant} dot /></td>
                <td className="px-4 py-3 text-center">
                  {!r.isInstallment && r.status === 'paid' && (
                    <button
                      onClick={() => paymentsApi.downloadQuittance(r.payment.id,
                        docFilename('quittance', { tenant: r.payment.tenant_full_name, property: r.payment.property_name, month: r.payment.period_month, year: r.payment.period_year }))}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 transition-colors">
                      <Download size={11} /> Quittance
                    </button>
                  )}
                  {showDeclare && r.isInstallment && (r.status === 'pending' || r.status === 'late') && (
                    <button onClick={() => declareInst(r.planId!, r.seq!)} disabled={declaring === `${r.planId}-${r.seq}`}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-white disabled:opacity-50" style={{ background: '#0D2F5C' }}>
                      <Send size={11} /> {declaring === `${r.planId}-${r.seq}` ? 'Envoi…' : 'Déclarer'}
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes paiements</h1>
        <p className="text-gray-500 text-sm mt-1">Vos règlements passés et à venir (loyers et plans d'apurement)</p>
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

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 py-12 text-center text-gray-400 text-sm">Chargement…</div>
      ) : rows.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 py-12 text-center text-gray-400">
          <CreditCard size={32} className="mx-auto mb-2 text-gray-300" />
          <p className="text-sm">Aucun paiement enregistré</p>
        </div>
      ) : (
        <div className="space-y-6">
          {upcoming.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-1.5"><CalendarClock size={15} className="text-blue-500" /> À venir / en attente</h2>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">{renderTable(upcoming, true)}</div>
            </div>
          )}
          <div>
            <h2 className="text-sm font-semibold text-gray-900 mb-2">Historique</h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {history.length > 0 ? renderTable(history, false)
                : <div className="py-8 text-center text-gray-400 text-sm">Aucun règlement enregistré pour l'instant.</div>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
