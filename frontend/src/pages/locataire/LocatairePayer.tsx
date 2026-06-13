import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Banknote, CheckCircle, Wallet, Clock, ChevronRight } from 'lucide-react'
import { apiClient } from '@/api/client'
import { paymentsApi } from '@/api/payments'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { StatusBadge } from '@/components/common/StatusBadge'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
const r2 = (n: number) => Math.round(n * 100) / 100

const METHODS = [
  { id: 'virement', icon: Building2, label: 'Virement bancaire', desc: 'SEPA, délai 1-2 jours', color: '#059669' },
  { id: 'especes', icon: Banknote, label: 'Espèces', desc: 'En agence ou à l\'accueil', color: '#DC2626' },
]

// Statut d'une écriture côté locataire (cycle de vie d'un règlement) :
// à régler -> (je déclare) en attente -> (le gestionnaire confirme) validé.
type StatutKey = 'valide' | 'attente' | 'a_regler' | 'retard' | 'partiel' | 'applique'
const STATUT: Record<StatutKey, { label: string; variant: 'green' | 'blue' | 'yellow' | 'red' | 'gray' }> = {
  valide:   { label: 'Validé',     variant: 'green' },
  attente:  { label: 'En attente', variant: 'yellow' },
  a_regler: { label: 'À régler',   variant: 'blue' },
  retard:   { label: 'En retard',  variant: 'red' },
  partiel:  { label: 'Partiel',    variant: 'yellow' },
  applique: { label: 'Appliquée',  variant: 'green' },
}

// Statut du RESTE À CHARGE d'un mois (part réellement à la charge du locataire,
// hors APL). `tenantPaid` = ce qui a été payé au-delà de l'APL ; `reste` = sa part due.
function resteStatut(tenantPaid: number, reste: number, declared: boolean): StatutKey {
  if (tenantPaid >= reste - 0.005) return 'valide'
  if (declared) return 'attente'
  if (tenantPaid > 0.005) return 'partiel'
  return 'a_regler'
}

export default function LocatairePayer() {
  const navigate = useNavigate()
  const [payment, setPayment] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [allPayments, setAllPayments] = useState<any[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])

  const load = useCallback(async () => {
    const [cur, lst, pl] = await Promise.allSettled([
      apiClient.get('/payments/locataire/current'),
      paymentsApi.list({ limit: 120 }),
      apurementApi.mine(),
    ])
    if (cur.status === 'fulfilled') setPayment(cur.value.data.payment)
    if (lst.status === 'fulfilled') setAllPayments(lst.value.data.items ?? lst.value.data)
    if (pl.status === 'fulfilled') setPlans(pl.value.data)
  }, [])

  useEffect(() => { load().finally(() => setIsLoading(false)) }, [load])

  // Solde actuel = cumul du reste à payer (loyers non soldés + échéances d'apurement
  // non réglées), tous mois confondus.
  const soldeActuel = r2(
    allPayments.filter((p: any) => p.status !== 'cancelled')
      .reduce((s: number, p: any) => s + (Number(p.balance ?? 0) || 0), 0)
    + plans.flatMap(pl => pl.installments).filter(i => !i.paid).reduce((s, i) => s + i.amount, 0)
  )

  // Historique : uniquement les écritures DATÉES, c.-à-d. les paiements validés ou
  // en attente (et l'APL appliquée). Les sommes non réglées (à régler / en retard)
  // ne figurent pas ici : elles sont reflétées par le solde et le bouton de paiement.
  type Row = { key: string; date: string; intitule: string; montant: number; statut: StatutKey; rank: number }
  const history: Row[] = []
  for (const p of allPayments) {
    if (p.status === 'cancelled' || p.settled_by_plan) continue
    const due = Number(p.amount_due || 0)
    const apl = Math.min(Number(p.amount_apl || 0), due)
    const reste = r2(due - apl)
    const tenantPaid = r2(Number(p.amount_paid || 0) - apl)
    if (apl > 0.005)
      history.push({ key: `apl-${p.id}`, date: p.due_date, intitule: `Aide personnelle au logement · ${p.period_label}`, montant: apl, statut: 'applique', rank: 1 })
    if (reste > 0.005) {
      const statut = resteStatut(tenantPaid, reste, !!p.declared_at)
      // Montant affiché = le règlement concerné : la somme DÉCLARÉE quand c'est en
      // attente, la somme RÉELLEMENT payée (hors APL) quand c'est validé/partiel.
      let montant = reste
      let date: string | null = null
      if (statut === 'attente') {
        montant = Number(p.declared_amount ?? reste) || reste
        date = p.declared_at || p.due_date
      } else if (statut === 'valide' || statut === 'partiel') {
        montant = tenantPaid > 0.005 ? tenantPaid : reste
        date = p.payment_date || p.due_date
      }
      if (date)
        history.push({ key: `reste-${p.id}`, date, intitule: `Règlement · ${p.period_label}`, montant, statut, rank: 2 })
    }
  }
  for (const pl of plans) {
    for (const i of pl.installments) {
      if (i.paid)
        history.push({ key: `i-${pl.id}-${i.seq}`, date: i.paid_date || i.due_date, intitule: `Plan d'apurement · échéance ${i.seq}`, montant: i.amount, statut: 'valide', rank: 3 })
      else if (i.declared)
        history.push({ key: `i-${pl.id}-${i.seq}`, date: i.declared_date || i.due_date, intitule: `Plan d'apurement · échéance ${i.seq}`, montant: i.amount, statut: 'attente', rank: 3 })
    }
  }
  history.sort((a, b) => b.date.localeCompare(a.date) || a.rank - b.rank)

  const due = Number(payment?.balance ?? payment?.amount_due) || 0
  const isDeclared = payment && payment.declared_at && payment.status !== 'paid'

  if (isLoading) {
    return <div className="p-6 flex items-center justify-center h-48"><p className="text-gray-400 text-sm">Chargement…</p></div>
  }

  return (
    <div className="p-4 sm:p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Payer mon loyer</h1>
        <p className="text-gray-500 text-sm mt-1">Solde, règlement et historique de votre loyer</p>
      </div>

      {/* Solde actuel */}
      <div className={`rounded-xl border p-5 mb-5 ${soldeActuel > 0.005 ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'}`}>
        <div className="flex items-center gap-3">
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${soldeActuel > 0.005 ? 'bg-amber-100' : 'bg-green-100'}`}>
            <Wallet size={20} className={soldeActuel > 0.005 ? 'text-amber-600' : 'text-green-600'} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide font-medium text-gray-500">Solde actuel</p>
            <p className={`text-2xl font-bold ${soldeActuel > 0.005 ? 'text-amber-700' : 'text-green-700'}`}>
              {soldeActuel > 0.005 ? fmtEuro(soldeActuel) : '0,00 €'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {soldeActuel > 0.005 ? 'Reste à payer, cumul de tous les mois et plans d\'apurement' : 'Vous êtes à jour'}
            </p>
          </div>
        </div>
      </div>

      {/* Moyens de paiement (au-dessus de l'historique). Un clic ouvre la page de règlement. */}
      {!payment || due <= 0.005 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <CheckCircle size={36} className="mx-auto mb-2 text-green-400" />
          <p className="text-gray-700 font-medium">Aucun loyer à régler</p>
          <p className="text-sm text-gray-400 mt-1">Vous êtes à jour dans vos paiements.</p>
        </div>
      ) : (
        <>
          {isDeclared && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-3 flex items-start gap-3">
              <Clock size={18} className="text-amber-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-amber-700">
                Un règlement de <strong>{fmtEuro(Number(payment.declared_amount ?? due))}</strong> est en attente de validation par votre gestionnaire.
                Vous pouvez en déclarer un autre ci-dessous si besoin.
              </p>
            </div>
          )}
          <p className="text-sm font-medium text-gray-700 mb-2">Régler mon loyer : choisissez un moyen de paiement</p>
          <div className="space-y-2 mb-2">
            {METHODS.map(m => {
              const Icon = m.icon
              return (
                <button
                  key={m.id}
                  onClick={() => navigate(`/locataire/payer/regler/${m.id}`)}
                  className="w-full flex items-center gap-4 p-4 rounded-xl border border-gray-200 text-left transition-all hover:border-gray-300 hover:bg-gray-50"
                >
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${m.color}15` }}>
                    <Icon size={18} style={{ color: m.color }} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">{m.label}</p>
                    <p className="text-xs text-gray-500">{m.desc}</p>
                  </div>
                  <ChevronRight size={18} className="text-gray-300 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </>
      )}

      {/* Historique des paiements (validés / en attente) */}
      {history.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold text-gray-900 mb-2">Historique des paiements</h2>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Intitulé</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Montant</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map(h => {
                  const st = STATUT[h.statut]
                  return (
                    <tr key={h.key} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{format(new Date(h.date), 'd MMM yyyy', { locale: fr })}</td>
                      <td className="px-4 py-3 text-sm text-gray-800">{h.intitule}</td>
                      <td className="px-4 py-3 text-right text-sm font-medium text-gray-900 whitespace-nowrap">{fmtEuro(h.montant)}</td>
                      <td className="px-4 py-3"><StatusBadge label={st.label} variant={st.variant} dot /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
