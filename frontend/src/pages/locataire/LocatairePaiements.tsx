import { useState, useEffect, useCallback } from 'react'
import { Wallet, Download } from 'lucide-react'
import { paymentsApi } from '@/api/payments'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { docFilename } from '@/utils/filename'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

// « 2026-05 » -> « Mai 2026 » (en-tête de regroupement du grand livre).
const monthLabel = (period: string) => {
  const [y, m] = period.split('-').map(Number)
  const s = format(new Date(y, (m || 1) - 1, 1), 'MMMM yyyy', { locale: fr })
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// Grand livre vu côté locataire :
//  • débit (rouge, signe −) = ce qui augmente sa dette : appel de loyer,
//    échéance d'apurement, régularisation de charges défavorable…
//  • crédit (vert, signe +) = ce qui la réduit : APL (prépaiement), reste à
//    charge réglé, règlement d'échéance, remboursement de charges favorable…
// Tri : par mois (le plus récent en haut), puis dans le mois selon `rank`
// (appel de loyer d'abord, puis APL, puis reste à charge, puis apurement).
interface Entry {
  key: string
  date: string | null
  period: string         // « AAAA-MM » : regroupe/ordonne les écritures par mois
  rank: number           // ordre dans le mois (0 = appel de loyer, en premier)
  intitule: string
  montant: number
  sign: 'debit' | 'credit'
  payment?: any          // pour la quittance (reste à charge / règlement payé)
  planId?: string        // pour la quittance d'échéance d'apurement
  seq?: number
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

  const pad = (m: number) => String(m).padStart(2, '0')
  const r2 = (n: number) => Math.round(n * 100) / 100
  const entries: Entry[] = []
  for (const p of payments) {
    if (p.status === 'cancelled') continue
    const period = `${p.period_year}-${pad(p.period_month)}`
    const due = Number(p.amount_due ?? 0)
    // amount_paid contient déjà l'APL (prépaiement tiers payant) : on isole donc
    // la part APL réellement appliquée et le reste à charge effectivement réglé,
    // pour ne pas compter l'APL deux fois.
    const aplApplied = Math.min(Number(p.amount_apl ?? 0), due)
    const reste = r2(Number(p.amount_paid ?? 0) - aplApplied)
    // 1. Appel de loyer (débit, en premier dans le mois)
    entries.push({ key: `app-${p.id}`, date: p.due_date, period, rank: 0,
      intitule: `Appel de loyer · ${p.period_label}`, montant: due, sign: 'debit' })
    // 2. APL : prépaiement (crédit)
    if (aplApplied > 0.005)
      entries.push({ key: `apl-${p.id}`, date: p.due_date, period, rank: 1,
        intitule: `Aide au logement (APL) · ${p.period_label}`, montant: aplApplied, sign: 'credit' })
    // 3. Reste à charge réglé par le locataire (crédit)
    if (reste > 0.005)
      entries.push({ key: `pay-${p.id}`, date: p.payment_date || p.due_date, period, rank: 2,
        intitule: `${aplApplied > 0.005 ? 'Reste à charge' : 'Règlement'} · ${p.period_label}`,
        montant: reste, sign: 'credit', payment: p })
  }
  for (const pl of plans) {
    for (const i of pl.installments) {
      const period = (i.due_date || '').slice(0, 7)
      entries.push({ key: `iap-${pl.id}-${i.seq}`, date: i.due_date, period, rank: 5,
        intitule: `Plan d'apurement · échéance ${i.seq}`, montant: i.amount, sign: 'debit' })
      if (i.paid)
        entries.push({ key: `ipa-${pl.id}-${i.seq}`, date: i.paid_date || i.due_date, period, rank: 6,
          intitule: `Règlement apurement · échéance ${i.seq}`, montant: i.amount, sign: 'credit', planId: pl.id, seq: i.seq })
    }
  }
  // Mois le plus récent en haut ; dans le mois, ordre métier via `rank`.
  entries.sort((a, b) =>
    b.period.localeCompare(a.period) || a.rank - b.rank || (b.date || '').localeCompare(a.date || ''))

  const totalDebits = entries.filter(e => e.sign === 'debit').reduce((s, e) => s + e.montant, 0)
  const totalCredits = entries.filter(e => e.sign === 'credit').reduce((s, e) => s + e.montant, 0)
  const solde = r2(totalDebits - totalCredits)

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
                {(() => {
                  // Les écritures sont déjà triées (mois récent en tête, puis appel
                  // → APL → reste à charge). On insère un en-tête à chaque changement
                  // de mois pour que le regroupement « par mois donné » soit explicite.
                  const out: JSX.Element[] = []
                  let lastPeriod: string | null = null
                  for (const e of entries) {
                    if (e.period !== lastPeriod) {
                      lastPeriod = e.period
                      out.push(
                        <tr key={`hdr-${e.period}`} className="bg-gray-50/60">
                          <td colSpan={3} className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                            {monthLabel(e.period)}
                          </td>
                        </tr>
                      )
                    }
                    out.push(
                  <tr key={e.key} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                      {e.date ? format(new Date(e.date), 'd MMM yyyy', { locale: fr }) : '·'}
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
                        {e.planId && e.seq != null && (
                          <button
                            onClick={() => apurementApi.downloadInstallmentQuittance(e.planId!, e.seq!, `quittance_apurement_echeance_${e.seq}.pdf`)}
                            title="Quittance de l'échéance"
                            className="text-green-600 hover:text-green-800"><Download size={13} /></button>
                        )}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-right text-sm font-medium whitespace-nowrap ${e.sign === 'credit' ? 'text-green-600' : 'text-red-600'}`}>
                      {e.sign === 'credit' ? `+ ${fmtEuro(e.montant)}` : `− ${fmtEuro(e.montant)}`}
                    </td>
                  </tr>
                    )
                  }
                  return out
                })()}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
