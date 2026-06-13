import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wallet, Download } from 'lucide-react'
import { LogoMark } from '@/components/common/Logo'
import { apiClient } from '@/api/client'
import { paymentsApi } from '@/api/payments'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { docFilename } from '@/utils/filename'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

// Libellé du type de paiement (sert d'intitulé pour la ligne de règlement).
const METHOD_LABELS: Record<string, string> = {
  virement: 'Virement', cheque: 'Chèque', prelevement: 'Prélèvement', especes: 'Espèces',
}

// Référence d'opération stable (déterministe) dérivée de l'id du paiement, façon
// relevé bancaire (ex. « 7BPWH4F »). Pas une vraie référence banque (pas d'import
// bancaire) : identifiant interne d'affichage, constant pour un paiement donné.
const payRef = (id: string) => {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (Math.imul(h, 31) + id.charCodeAt(i)) >>> 0
  return h.toString(36).toUpperCase().padStart(7, '0').slice(-7)
}

// Intitulés façon relevé de compte (majuscules).
const appelLabel = (p: any) => {
  const start = p.period_start ? new Date(p.period_start) : new Date(p.period_year, p.period_month - 1, 1)
  const end = p.period_end ? new Date(p.period_end) : new Date(p.period_year, p.period_month, 0)
  return `Appel pour la période du ${format(start, 'dd MMMM', { locale: fr })} au ${format(end, 'dd MMMM', { locale: fr })}`.toUpperCase()
}
const reglementLabel = (p: any) => {
  const label = METHOD_LABELS[p.payment_method] ?? 'Règlement'
  const ref = (p.payment_method === 'virement' || p.payment_method === 'cheque') ? ` N° ${payRef(p.id)}` : ''
  const d = p.payment_date ? ` du ${format(new Date(p.payment_date), 'dd/MM/yyyy')}` : ''
  const nom = p.tenant_full_name ? ` ${p.tenant_full_name}` : ''
  return `${label}${ref}${d}${nom}`.toUpperCase()
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

function SectionAvatar() {
  return (
    <span className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: '#0D2F5C' }}>
      <LogoMark size={18} className="text-white" />
    </span>
  )
}

export default function LocatairePaiements() {
  const navigate = useNavigate()
  const [payments, setPayments] = useState<any[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])
  const [regularizations, setRegularizations] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const [pr, pl, rg] = await Promise.allSettled([
        paymentsApi.list({ limit: 120 }),
        apurementApi.mine(),
        apiClient.get('/payments/locataire/regularizations'),
      ])
      if (pr.status === 'fulfilled') setPayments(pr.value.data.items ?? pr.value.data)
      if (pl.status === 'fulfilled') setPlans(pl.value.data)
      if (rg.status === 'fulfilled') setRegularizations(rg.value.data ?? [])
    } catch { /* ignore */ } finally { setIsLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const pad = (m: number) => String(m).padStart(2, '0')
  const r2 = (n: number) => Math.round(n * 100) / 100
  const entries: Entry[] = []
  for (const p of payments) {
    // Mois entièrement reporté sur un plan d'apurement (annulé ou « soldé apurement »
    // une fois le plan terminé) : exclu, la dette/les règlements vivent dans les échéances.
    if (p.status === 'cancelled' || p.settled_by_plan) continue
    const period = `${p.period_year}-${pad(p.period_month)}`
    const due = Number(p.amount_due ?? 0)
    // amount_paid contient déjà l'APL (prépaiement tiers payant) : on isole donc
    // la part APL réellement appliquée et le reste à charge effectivement réglé,
    // pour ne pas compter l'APL deux fois.
    const aplApplied = Math.min(Number(p.amount_apl ?? 0), due)
    const reste = r2(Number(p.amount_paid ?? 0) - aplApplied)
    // 1. Appel de loyer (débit, en premier dans le mois)
    entries.push({ key: `app-${p.id}`, date: p.due_date, period, rank: 0,
      intitule: appelLabel(p), montant: due, sign: 'debit' })
    // 2. APL : prépaiement (crédit)
    if (aplApplied > 0.005)
      entries.push({ key: `apl-${p.id}`, date: p.due_date, period, rank: 1,
        intitule: `Aide personnelle au logement · ${p.period_label}`.toUpperCase(), montant: aplApplied, sign: 'credit' })
    // 3. Règlement du locataire (crédit) : intitulé façon relevé de compte
    //    (type de paiement, n° d'opération, date, payeur). La quittance n'est
    //    proposée que si le mois est entièrement payé.
    if (reste > 0.005)
      entries.push({ key: `pay-${p.id}`, date: p.payment_date || p.due_date, period, rank: 2,
        intitule: reglementLabel(p),
        montant: reste, sign: 'credit', payment: p.status === 'paid' ? p : undefined })
    // 4. Part reportée sur un plan d'apurement (apurement partiel) : crédit qui sort
    //    cette part du solde du mois — la dette correspondante vit dans les échéances.
    if (Number(p.amount_on_plan ?? 0) > 0.005)
      entries.push({ key: `onplan-${p.id}`, date: p.payment_date || p.due_date, period, rank: 3,
        intitule: `Report sur plan d'apurement · ${p.period_label}`.toUpperCase(),
        montant: Number(p.amount_on_plan), sign: 'credit' })
  }
  // Régularisations annuelles de charges : créditrice (trop-perçu, crédit vert) ou
  // débitrice (complément dû, débit rouge). Non rattachée à un paiement -> aucun
  // double-comptage (l'application n'ajuste que la provision mensuelle future).
  for (const reg of regularizations) {
    const credit = Number(reg.balance) >= 0
    const ds = (reg.applied_at || reg.period_end || '').slice(0, 10) || null
    const year = reg.period_start ? new Date(reg.period_start).getFullYear()
      : reg.period_end ? new Date(reg.period_end).getFullYear() : ''
    entries.push({ key: `reg-${reg.id}`, date: ds, period: (ds || '').slice(0, 7), rank: 3,
      intitule: `Variable ${credit ? 'créditrice' : 'débitrice'} régularisation charges ${year}`.toUpperCase(),
      montant: Math.abs(Number(reg.balance) || 0), sign: credit ? 'credit' : 'debit' })
  }
  for (const pl of plans) {
    for (const i of pl.installments) {
      const period = (i.due_date || '').slice(0, 7)
      entries.push({ key: `iap-${pl.id}-${i.seq}`, date: i.due_date, period, rank: 5,
        intitule: `Plan d'apurement · échéance ${i.seq}`.toUpperCase(), montant: i.amount, sign: 'debit' })
      if (i.paid)
        entries.push({ key: `ipa-${pl.id}-${i.seq}`, date: i.paid_date || i.due_date, period, rank: 6,
          intitule: `Règlement apurement · échéance ${i.seq}`.toUpperCase(), montant: i.amount, sign: 'credit', planId: pl.id, seq: i.seq })
    }
  }
  // Tri chronologique : date la plus récente en haut ; à date égale, ordre métier
  // via `rank` (appel de loyer avant APL, avant reste à charge).
  entries.sort((a, b) =>
    (b.date || '').localeCompare(a.date || '') || a.rank - b.rank)

  const totalDebits = entries.filter(e => e.sign === 'debit').reduce((s, e) => s + e.montant, 0)
  const totalCredits = entries.filter(e => e.sign === 'credit').reduce((s, e) => s + e.montant, 0)
  const solde = r2(totalDebits - totalCredits)

  // Export CSV du grand livre (séparateur « ; » + BOM pour Excel FR).
  const handleExport = () => {
    const sep = ';'
    const esc = (s: string) => `"${(s || '').replace(/"/g, '""')}"`
    const lines = entries.map(e => [
      e.date ? format(new Date(e.date), 'dd/MM/yyyy') : '',
      esc(e.intitule),
      (e.sign === 'credit' ? '' : '-') + e.montant.toFixed(2).replace('.', ','),
    ].join(sep))
    // BOM UTF-8 (﻿) en tête pour qu'Excel reconnaisse l'encodage et affiche
    // correctement les accents (séquence d'échappement, fiable au build).
    const csv = String.fromCharCode(0xFEFF) + ['Date;Intitulé;Montant', ...lines].join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'ma_comptabilite.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  // Solde signé (+/-) : négatif rouge si reste à payer, positif vert si en faveur.
  const soldeDisplay = solde > 0.005
    ? { text: `− ${fmtEuro(solde)}`, cls: 'text-red-600' }
    : solde < -0.005
      ? { text: `+ ${fmtEuro(-solde)}`, cls: 'text-green-600' }
      : { text: '0,00 €', cls: 'text-gray-700' }

  return (
    <div className="p-4 sm:p-6 space-y-5">
      {/* Mon compte */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <SectionAvatar />
            <h2 className="text-lg font-bold" style={{ color: '#0E9F8E' }}>Mon compte</h2>
          </div>
          <button
            onClick={() => navigate('/locataire/payer')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white flex-shrink-0"
            style={{ background: '#0D2F5C' }}
          >
            <Wallet size={15} /> Payer
          </button>
        </div>
        <div className="px-5 py-10 flex items-center justify-center text-center" style={{ background: '#F0F9FA' }}>
          <p className="text-base">
            <span className="text-gray-600 font-medium">Solde actuel : </span>
            <span className={`text-xl font-bold ${soldeDisplay.cls}`}>{soldeDisplay.text}</span>
          </p>
        </div>
        <p className="px-5 pb-4 -mt-1 text-center text-xs text-gray-500">
          {solde > 0.005 ? 'Reste à payer (cumul de tous les mois et plans d\'apurement)' : solde < -0.005 ? 'En votre faveur' : 'Vous êtes à jour dans vos règlements'}
        </p>
      </div>

      {/* Ma comptabilité */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <SectionAvatar />
            <h2 className="text-lg font-bold" style={{ color: '#0E9F8E' }}>Ma comptabilité</h2>
          </div>
          {entries.length > 0 && (
            <button
              onClick={handleExport}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white flex-shrink-0"
              style={{ background: '#0D2F5C' }}
            >
              <Download size={15} /> Exporter
            </button>
          )}
        </div>
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
                      {e.date ? format(new Date(e.date), 'd MMM yyyy', { locale: fr }) : '·'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-800">
                      <span className="inline-flex items-center gap-2">
                        {e.intitule}
                        {e.payment && (
                          <button
                            onClick={() => paymentsApi.downloadQuittance(e.payment.id,
                              docFilename('quittance', { tenant: e.payment.tenant_full_name, property: e.payment.property_name, month: e.payment.period_month, year: e.payment.period_year }))}
                            className="inline-flex items-center gap-1 text-xs font-medium text-green-600 hover:text-green-800 hover:underline">
                            <Download size={12} /> Quittance
                          </button>
                        )}
                        {e.planId && e.seq != null && (
                          <button
                            onClick={() => apurementApi.downloadInstallmentQuittance(e.planId!, e.seq!, `quittance_apurement_echeance_${e.seq}.pdf`)}
                            className="inline-flex items-center gap-1 text-xs font-medium text-green-600 hover:text-green-800 hover:underline">
                            <Download size={12} /> Quittance
                          </button>
                        )}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-right text-sm font-medium whitespace-nowrap ${e.sign === 'credit' ? 'text-green-600' : 'text-red-600'}`}>
                      {e.sign === 'credit' ? `+ ${fmtEuro(e.montant)}` : `− ${fmtEuro(e.montant)}`}
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
