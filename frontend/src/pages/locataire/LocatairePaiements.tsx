import { useState, useEffect, useCallback } from 'react'
import { Wallet, Download } from 'lucide-react'
import { paymentsApi } from '@/api/payments'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { docFilename } from '@/utils/filename'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

interface Entry {
  key: string
  date: string | null
  intitule: string
  montant: number
  kind: 'appel' | 'paiement'
  payment?: any          // pour la quittance (règlement de loyer payé)
}

export default function LocatairePaiements() {
  const [payments, setPayments] = useState<any[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const [pr, pl] = await Promise.allSettled([
        paymentsApi.list({ limit: 120 }),
        apurementApi.mine(),
      ])
      if (pr.status === 'fulfilled') setPayments(pr.value.data.items ?? pr.value.data)
      if (pl.status === 'fulfilled') setPlans(pl.value.data)
    } catch { /* ignore */ } finally { setIsLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  // Grand livre : un appel (débit) et, le cas échéant, l'aide au logement + le
  // règlement (crédits) par loyer ; idem pour chaque échéance de plan d'apurement.
  const entries: Entry[] = []
  for (const p of payments) {
    if (p.status === 'cancelled') continue
    entries.push({ key: `app-${p.id}`, date: p.due_date, intitule: `Appel de loyer · ${p.period_label}`, montant: p.amount_due ?? 0, kind: 'appel' })
    if ((p.amount_apl ?? 0) > 0)
      entries.push({ key: `apl-${p.id}`, date: p.due_date, intitule: `Aide au logement (APL) · ${p.period_label}`, montant: p.amount_apl, kind: 'paiement' })
    if ((p.amount_paid ?? 0) > 0)
      entries.push({ key: `pay-${p.id}`, date: p.payment_date || p.due_date, intitule: `Règlement · ${p.period_label}`, montant: p.amount_paid, kind: 'paiement', payment: p })
  }
  for (const pl of plans) {
    for (const i of pl.installments) {
      entries.push({ key: `iap-${pl.id}-${i.seq}`, date: i.due_date, intitule: `Plan d'apurement · échéance ${i.seq}`, montant: i.amount, kind: 'appel' })
      if (i.paid)
        entries.push({ key: `ipa-${pl.id}-${i.seq}`, date: i.paid_date || i.due_date, intitule: `Règlement apurement · échéance ${i.seq}`, montant: i.amount, kind: 'paiement' })
    }
  }
  entries.sort((a, b) => (b.date || '').localeCompare(a.date || ''))

  const totalAppels = entries.filter(e => e.kind === 'appel').reduce((s, e) => s + e.montant, 0)
  const totalPaiements = entries.filter(e => e.kind === 'paiement').reduce((s, e) => s + e.montant, 0)
  const solde = Math.round((totalAppels - totalPaiements) * 100) / 100

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Ma comptabilité</h1>
        <p className="text-gray-500 text-sm mt-1">Solde et grand livre de vos appels de loyer et règlements</p>
      </div>

      {/* Solde actuel */}
      <div className={`rounded-xl border p-5 mb-5 ${solde > 0.005 ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'}`}>
        <div className="flex items-center gap-3">
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${solde > 0.005 ? 'bg-amber-100' : 'bg-green-100'}`}>
            <Wallet size={20} className={solde > 0.005 ? 'text-amber-600' : 'text-green-600'} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide font-medium text-gray-500">Solde actuel</p>
            <p className={`text-2xl font-bold ${solde > 0.005 ? 'text-amber-700' : 'text-green-700'}`}>
              {solde > 0.005 ? fmtEuro(solde) : solde < -0.005 ? `${fmtEuro(-solde)} en votre faveur` : '0,00 €'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {solde > 0.005 ? 'Reste à payer (cumul de tous les mois et plans d\'apurement)' : 'Vous êtes à jour dans vos règlements'}
            </p>
          </div>
        </div>
      </div>

      {/* Grand livre */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
        ) : entries.length === 0 ? (
          <div className="py-12 text-center text-gray-400">
            <Wallet size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucune écriture pour le moment</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px]">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Intitulé</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Montant</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.map(e => (
                  <tr key={e.key} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                      {e.date ? format(new Date(e.date), 'd MMM yyyy', { locale: fr }) : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-800">
                      <span className="inline-flex items-center gap-2">
                        {e.intitule}
                        {e.payment && (
                          <button
                            onClick={() => paymentsApi.downloadQuittance(e.payment.id,
                              docFilename('quittance', { tenant: e.payment.tenant_full_name, property: e.payment.property_name, month: e.payment.period_month, year: e.payment.period_year }))}
                            title="Quittance"
                            className="text-green-600 hover:text-green-800"><Download size={13} /></button>
                        )}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-right text-sm font-medium whitespace-nowrap ${e.kind === 'paiement' ? 'text-green-600' : 'text-gray-900'}`}>
                      {e.kind === 'paiement' ? `− ${fmtEuro(e.montant)}` : fmtEuro(e.montant)}
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
