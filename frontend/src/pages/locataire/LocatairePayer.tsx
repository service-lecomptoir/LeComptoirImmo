import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Building2, Banknote, CheckCircle, Wallet, Clock, CreditCard, Download, CalendarClock, ChevronDown, ChevronRight } from 'lucide-react'
import { apiClient } from '@/api/client'
import { paymentsApi } from '@/api/payments'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { onlinePaymentsApi } from '@/api/onlinePayments'
import { BRAND } from '@/lib/brand'
import { toast } from '@/store/toast'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Button } from '@/components/ui'
import { docFilename } from '@/utils/filename'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
const r2 = (n: number) => Math.round(n * 100) / 100

const METHODS = [
  { id: 'virement', icon: Building2, label: 'Virement bancaire', desc: 'SEPA, délai 1-2 jours', color: '#059669' },
  { id: 'especes', icon: Banknote, label: 'Espèces', desc: 'En agence ou à l\'accueil', color: '#DC2626' },
]

// Côté locataire, un règlement n'a que deux états : « en attente » (déclaré, le
// gestionnaire doit confirmer) ou « validé » (confirmé / reçu). Les notions de
// partiel ou d'APL appliquée sont gérées côté gestionnaire ; ici, l'APL reçue et
// tout paiement confirmé apparaissent comme « validé ».
type StatutKey = 'valide' | 'attente'
const STATUT: Record<StatutKey, { label: string; variant: 'green' | 'yellow' }> = {
  valide:  { label: 'Validé',     variant: 'green' },
  attente: { label: 'En attente', variant: 'yellow' },
}

export default function LocatairePayer() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [payment, setPayment] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [allPayments, setAllPayments] = useState<any[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])
  // Disponibilité du paiement par carte (selon la config du gestionnaire).
  const [cardAvail, setCardAvail] = useState<{ available: boolean; provider: string | null }>({ available: false, provider: null })
  const [cardBusy, setCardBusy] = useState(false)

  const load = useCallback(async () => {
    const [cur, lst, pl, av] = await Promise.allSettled([
      apiClient.get('/payments/locataire/current'),
      paymentsApi.list({ limit: 120 }),
      apurementApi.mine(),
      onlinePaymentsApi.availability(),
    ])
    if (cur.status === 'fulfilled') setPayment(cur.value.data.payment)
    if (lst.status === 'fulfilled') setAllPayments(lst.value.data.items ?? lst.value.data)
    if (pl.status === 'fulfilled') setPlans(pl.value.data)
    if (av.status === 'fulfilled') setCardAvail(av.value.data)
  }, [])

  useEffect(() => { load().finally(() => setIsLoading(false)) }, [load])

  // Retour depuis le paiement par carte (Stripe Checkout).
  useEffect(() => {
    const card = searchParams.get('card')
    if (!card) return
    if (card === 'success') toast.success('Paiement par carte confirmé. Votre loyer est enregistré.')
    else if (card === 'cancel') toast.info('Paiement par carte annulé.')
    searchParams.delete('card')
    setSearchParams(searchParams, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Lance le paiement par carte : Stripe (redirection) ou SumUp (widget).
  const payByCard = async () => {
    if (!payment?.id) return
    setCardBusy(true)
    try {
      const { data } = await onlinePaymentsApi.checkout(payment.id)
      if (data.provider === 'stripe' && data.url) {
        window.location.href = data.url
      } else if (data.provider === 'sumup' && data.checkout_id) {
        navigate('/locataire/payer/carte', { state: { checkoutId: data.checkout_id, amount: data.amount } })
      } else {
        toast.error('Paiement par carte indisponible pour le moment.')
        setCardBusy(false)
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Impossible de démarrer le paiement par carte.')
      setCardBusy(false)
    }
  }

  // Déclaration du règlement d'une échéance d'apurement (passe « en attente »,
  // le gestionnaire valide ensuite, comme un loyer).
  const [declaringInst, setDeclaringInst] = useState<string | null>(null)
  // Bloc « Appels de loyer : apurement » replié par défaut.
  const [apurOpen, setApurOpen] = useState(false)
  const declareInst = async (planId: string, seq: number) => {
    setDeclaringInst(`${planId}-${seq}`)
    try {
      await apurementApi.declareInstallment(planId, seq)
      toast.success('Règlement de l\'échéance déclaré. En attente de validation.')
      await load()
    } catch {
      toast.error('Impossible de déclarer le règlement.')
    } finally {
      setDeclaringInst(null)
    }
  }
  // Échéances d'apurement encore dues (appels de loyer apurement à régler).
  const dueInstallments = plans.flatMap(pl =>
    (pl.installments || []).filter(i => !i.paid).map(i => ({ pl, i }))
  )

  // Solde actuel = cumul du reste à payer (loyers non soldés + échéances d'apurement
  // non réglées), tous mois confondus.
  const soldeActuel = r2(
    allPayments.filter((p: any) => p.status !== 'cancelled')
      .reduce((s: number, p: any) => s + (Number(p.balance ?? 0) || 0), 0)
    + plans.flatMap(pl => pl.installments).filter(i => !i.paid).reduce((s, i) => s + i.amount, 0)
  )

  // Solde restant couvert par un (des) plan(s) d'apurement en cours (échéances non
  // encore réglées). Sert à expliquer un solde négatif quand aucun loyer courant
  // n'est à régler : ce n'est pas « à jour », c'est un apurement en cours.
  const planDue = r2(
    plans.flatMap(pl => pl.installments).filter(i => !i.paid).reduce((s, i) => s + i.amount, 0)
  )

  // Historique : uniquement les écritures DATÉES, c.-à-d. les paiements validés ou
  // en attente (et l'APL appliquée). Les sommes non réglées (à régler / en retard)
  // ne figurent pas ici : elles sont reflétées par le solde et le bouton de paiement.
  type Row = { key: string; date: string; intitule: string; montant: number; statut: StatutKey; rank: number; payment?: any; planId?: string; seq?: number }
  const history: Row[] = []
  for (const p of allPayments) {
    if (p.status === 'cancelled' || p.settled_by_plan) continue
    const due = Number(p.amount_due || 0)
    const apl = Math.min(Number(p.amount_apl || 0), due)
    const reste = r2(due - apl)
    const tenantPaid = r2(Number(p.amount_paid || 0) - apl)
    // APL : crédit reçu (tiers payant) -> validé.
    if (apl > 0.005)
      history.push({ key: `apl-${p.id}`, date: p.due_date, intitule: `Aide personnelle au logement · ${p.period_label}`, montant: apl, statut: 'valide', rank: 1 })
    // Règlement du locataire : déclaré (en attente, montant déclaré) ou confirmé
    // (validé, montant réellement payé hors APL). La quittance n'est proposée que
    // si TOUT le mois est payé.
    if (reste > 0.005) {
      if (p.declared_at)
        history.push({ key: `reste-${p.id}`, date: p.declared_at, intitule: `Règlement · ${p.period_label}`, montant: Number(p.declared_amount ?? reste) || reste, statut: 'attente', rank: 2 })
      else if (tenantPaid > 0.005)
        history.push({ key: `reste-${p.id}`, date: p.payment_date || p.due_date, intitule: `Règlement · ${p.period_label}`, montant: tenantPaid, statut: 'valide', rank: 2, payment: p.status === 'paid' ? p : undefined })
    }
  }
  for (const pl of plans) {
    for (const i of pl.installments) {
      if (i.paid)
        history.push({ key: `i-${pl.id}-${i.seq}`, date: i.paid_date || i.due_date, intitule: `Plan d'apurement · échéance ${i.seq}`, montant: i.amount, statut: 'valide', rank: 3, planId: pl.id, seq: i.seq })
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
        <div className="flex flex-col items-center text-center gap-2">
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${soldeActuel > 0.005 ? 'bg-amber-100' : 'bg-green-100'}`}>
            <Wallet size={20} className={soldeActuel > 0.005 ? 'text-amber-600' : 'text-green-600'} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide font-medium text-gray-500">Solde actuel</p>
            <p className={`text-2xl font-bold ${soldeActuel > 0.005 ? 'text-red-600' : soldeActuel < -0.005 ? 'text-green-600' : 'text-gray-700'}`}>
              {soldeActuel > 0.005 ? `− ${fmtEuro(soldeActuel)}` : soldeActuel < -0.005 ? `+ ${fmtEuro(-soldeActuel)}` : '0,00 €'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {soldeActuel > 0.005 ? 'Reste à payer, cumul de tous les mois et plans d\'apurement' : 'Vous êtes à jour'}
            </p>
          </div>
        </div>
      </div>

      {/* Appels de loyer : apurement — échéances dues, à régler (déclaration). */}
      {dueInstallments.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5">
          <button
            type="button"
            onClick={() => setApurOpen(o => !o)}
            className="w-full flex items-center gap-2 text-left"
          >
            {apurOpen ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
            <CalendarClock size={16} className="text-amber-600" />
            <p className="text-sm font-semibold text-gray-800">Appels de loyer : apurement</p>
            <span className="ml-auto text-xs text-gray-400">{dueInstallments.length}</span>
          </button>
          {apurOpen && (
          <>
          <div className="divide-y divide-gray-100 mt-3">
            {dueInstallments.map(({ pl, i }) => (
              <div key={`${pl.id}-${i.seq}`} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <p className="text-sm text-gray-800">Apurement : échéance {i.seq}</p>
                  <p className="text-xs text-gray-400">Échéance du {format(new Date(i.due_date), 'd MMM yyyy', { locale: fr })}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-sm font-semibold text-gray-900">{fmtEuro(i.amount)}</span>
                  {i.declared ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">En attente</span>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => declareInst(pl.id, i.seq)}
                      isLoading={declaringInst === `${pl.id}-${i.seq}`}
                    >
                      Régler
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Réglez le montant par votre moyen habituel (virement, espèces), puis cliquez sur « Régler » pour le déclarer. Votre gestionnaire confirmera la réception.
          </p>
          </>
          )}
        </div>
      )}

      {/* Moyens de paiement (au-dessus de l'historique). Un clic ouvre la page de règlement. */}
      {!payment || due <= 0.005 ? (
        planDue > 0.005 ? (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 flex items-start gap-3">
            <Clock size={20} className="text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-gray-800 font-medium">Aucun loyer courant à régler</p>
              <p className="text-sm text-gray-600 mt-1">
                Votre solde restant (<strong>− {fmtEuro(planDue)}</strong>) est couvert par un <strong>plan d'apurement</strong>.
                Vous ne recevez pas de rappels d'impayés et vous le réglez en plusieurs fois selon l'échéancier convenu.
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <CheckCircle size={36} className="mx-auto mb-2 text-green-400" />
            <p className="text-gray-700 font-medium">Aucun loyer à régler</p>
            <p className="text-sm text-gray-400 mt-1">Vous êtes à jour dans vos paiements.</p>
          </div>
        )
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
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: `${BRAND.navy}15` }}>
              <CreditCard size={18} style={{ color: BRAND.navy }} />
            </div>
            <p className="text-sm font-semibold text-gray-800">Choisissez votre moyen de paiement</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-2">
            {METHODS.map(m => {
              const Icon = m.icon
              return (
                <button
                  key={m.id}
                  onClick={() => navigate(`/locataire/payer/regler/${m.id}`)}
                  className="flex flex-col items-center gap-2 p-4 rounded-xl border border-gray-200 text-center transition-all hover:border-gray-300 hover:bg-gray-50"
                >
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${m.color}15` }}>
                    <Icon size={20} style={{ color: m.color }} />
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{m.label}</p>
                  <p className="text-xs text-gray-500">{m.desc}</p>
                </button>
              )
            })}
            {/* Carte bancaire : proposée seulement si le gestionnaire l'a activée, sinon grisée. */}
            <button
              onClick={payByCard}
              disabled={!cardAvail.available || cardBusy}
              title={cardAvail.available ? 'Payer par carte bancaire' : "Votre gestionnaire ne propose pas le paiement par carte"}
              className={`flex flex-col items-center gap-2 p-4 rounded-xl border text-center transition-all ${
                cardAvail.available
                  ? 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 cursor-pointer'
                  : 'border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed'
              }`}
            >
              <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${BRAND.navy}15` }}>
                <CreditCard size={20} style={{ color: BRAND.navy }} />
              </div>
              <p className="text-sm font-semibold text-gray-900">{cardBusy ? 'Redirection…' : 'Carte bancaire'}</p>
              <p className="text-xs text-gray-500">{cardAvail.available ? 'Paiement immédiat sécurisé' : 'Non proposé'}</p>
            </button>
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
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Intitulé</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Montant</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map(h => {
                  const st = STATUT[h.statut]
                  return (
                    <tr key={h.key} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{format(new Date(h.date), 'd MMM yyyy', { locale: fr })}</td>
                      <td className="px-4 py-3 text-sm text-gray-800">
                        <span className="inline-flex items-center gap-2">
                          {h.intitule}
                          {h.payment && (
                            <button
                              onClick={() => paymentsApi.downloadQuittance(h.payment.id,
                                docFilename('quittance', { tenant: h.payment.tenant_full_name, property: h.payment.property_name, month: h.payment.period_month, year: h.payment.period_year }))}
                              title="Quittance" className="text-green-600 hover:text-green-800"><Download size={13} /></button>
                          )}
                          {h.planId && h.seq != null && (
                            <button
                              onClick={() => apurementApi.downloadInstallmentQuittance(h.planId!, h.seq!, `quittance_apurement_echeance_${h.seq}.pdf`)}
                              title="Quittance de l'échéance" className="text-green-600 hover:text-green-800"><Download size={13} /></button>
                          )}
                        </span>
                      </td>
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
