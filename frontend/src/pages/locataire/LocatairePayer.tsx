import { useState, useEffect, useCallback } from 'react'
import { Building2, Banknote, CheckCircle, AlertCircle, Wallet, Clock } from 'lucide-react'
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
// à régler -> (je déclare) en attente de validation -> (le gestionnaire confirme) validé.
type StatutKey = 'valide' | 'attente' | 'a_regler' | 'retard' | 'partiel' | 'applique'
const STATUT: Record<StatutKey, { label: string; variant: 'green' | 'blue' | 'yellow' | 'red' | 'gray' }> = {
  valide:   { label: 'Validé',     variant: 'green' },
  attente:  { label: 'En attente', variant: 'yellow' },
  a_regler: { label: 'À régler',   variant: 'blue' },
  retard:   { label: 'En retard',  variant: 'red' },
  partiel:  { label: 'Partiel',    variant: 'yellow' },
  applique: { label: 'Appliquée',  variant: 'green' },
}

const MONTHS = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

// Statut du RESTE À CHARGE d'un mois (part réellement à la charge du locataire,
// hors APL). Cycle : à régler -> en attente (déclaré) -> validé. `tenantPaid` est
// ce que le locataire a payé au-delà de l'APL ; `reste` sa part totale due.
function resteStatut(tenantPaid: number, reste: number, declared: boolean, dueDate: string | null, todayIso: string): StatutKey {
  if (tenantPaid >= reste - 0.005) return 'valide'
  if (declared) return 'attente'
  if (tenantPaid > 0.005) return 'partiel'
  if (dueDate && dueDate < todayIso) return 'retard'
  return 'a_regler'
}

export default function LocatairePayer() {
  const [payment, setPayment] = useState<any>(null)
  const [payee, setPayee] = useState<{ name?: string; address?: string; iban?: string; bic?: string } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [method, setMethod] = useState<string | null>(null)
  const [amount, setAmount] = useState<number>(0)
  const [isSending, setIsSending] = useState(false)
  const [allPayments, setAllPayments] = useState<any[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])

  const load = useCallback(async () => {
    const [cur, lst, pl] = await Promise.allSettled([
      apiClient.get('/payments/locataire/current'),
      paymentsApi.list({ limit: 120 }),
      apurementApi.mine(),
    ])
    if (cur.status === 'fulfilled') {
      setPayment(cur.value.data.payment)
      setPayee(cur.value.data.payee ?? null)
      if (cur.value.data.payment) {
        const p = cur.value.data.payment
        setAmount(Number(p.balance ?? p.amount_due) || 0)
      }
    }
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

  // Historique des paiements (côté locataire) : aide au logement (prépaiement),
  // reste à payer du mois, et échéances de plan d'apurement, avec leur statut.
  const todayIso = new Date().toISOString().slice(0, 10)
  type Row = { key: string; date: string | null; intitule: string; echeance: string | null; montant: number; statut: StatutKey; sort: string }
  const history: Row[] = []
  for (const p of allPayments) {
    if (p.status === 'cancelled' || p.settled_by_plan) continue   // mois reporté : la dette vit dans le plan
    const due = Number(p.amount_due || 0)
    const apl = Math.min(Number(p.amount_apl || 0), due)
    const reste = r2(due - apl)
    const tenantPaid = r2(Number(p.amount_paid || 0) - apl)
    if (apl > 0.005)
      history.push({ key: `apl-${p.id}`, date: p.due_date, intitule: `Aide personnelle au logement · ${p.period_label}`,
        echeance: p.due_date, montant: apl, statut: 'applique', sort: (p.due_date || '') + '-1' })
    if (reste > 0.005)
      history.push({ key: `reste-${p.id}`, date: tenantPaid > 0.005 ? (p.payment_date || null) : null,
        intitule: `Reste à payer · ${p.period_label}`, echeance: p.due_date, montant: reste,
        statut: resteStatut(tenantPaid, reste, !!p.declared_at, p.due_date || null, todayIso), sort: (p.due_date || '') + '-2' })
  }
  for (const pl of plans) {
    for (const i of pl.installments) {
      const statut: StatutKey = i.paid ? 'valide' : i.declared ? 'attente' : (i.due_date < todayIso ? 'retard' : 'a_regler')
      history.push({ key: `i-${pl.id}-${i.seq}`, date: i.paid ? (i.paid_date || i.due_date) : null,
        intitule: `Plan d'apurement · échéance ${i.seq}`, echeance: i.due_date, montant: i.amount, statut, sort: (i.due_date || '') + '-3' })
    }
  }
  history.sort((a, b) => b.sort.localeCompare(a.sort))

  const handleDeclare = async () => {
    if (!method || !payment || amount <= 0) return
    setIsSending(true)
    try {
      await apiClient.post('/payments/locataire/declare', { method, amount, payment_id: payment.id })
      setMethod(null)
      setIsLoading(true)
      await load()
      setIsLoading(false)
    } finally {
      setIsSending(false)
    }
  }

  // ── Cartes / blocs réutilisés ───────────────────────────────────────────────
  const soldeCard = (
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
  )

  const historyTable = history.length === 0 ? null : (
    <div className="mt-8">
      <h2 className="text-sm font-semibold text-gray-900 mb-2">Historique des paiements</h2>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Intitulé</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Échéance</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Montant</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {history.map(h => {
                const st = STATUT[h.statut]
                return (
                  <tr key={h.key} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{h.date ? format(new Date(h.date), 'd MMM yyyy', { locale: fr }) : '·'}</td>
                    <td className="px-4 py-3 text-sm text-gray-800">{h.intitule}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{h.echeance ? format(new Date(h.echeance), 'd MMM yyyy', { locale: fr }) : '·'}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-gray-900 whitespace-nowrap">{fmtEuro(h.montant)}</td>
                    <td className="px-4 py-3"><StatusBadge label={st.label} variant={st.variant} dot /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-48">
        <p className="text-gray-400 text-sm">Chargement…</p>
      </div>
    )
  }

  const due = Number(payment?.balance ?? payment?.amount_due) || 0
  const isDeclared = payment && payment.declared_at && payment.status !== 'paid'

  // ── Bloc « régler mon loyer » (modes de paiement, en bas) ───────────────────
  let payBlock: JSX.Element
  if (!payment || due <= 0.005) {
    payBlock = (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <CheckCircle size={36} className="mx-auto mb-2 text-green-400" />
        <p className="text-gray-700 font-medium">Aucun loyer à régler</p>
        <p className="text-sm text-gray-400 mt-1">Vous êtes à jour dans vos paiements.</p>
      </div>
    )
  } else if (isDeclared) {
    payBlock = (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <Clock size={20} className="text-amber-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold text-amber-800">Paiement en attente de validation</p>
            <p className="text-sm text-amber-700 mt-1">
              Vous avez déclaré un règlement de <strong>{fmtEuro(Number(payment.declared_amount ?? amount))}</strong>
              {payment.declared_method && <> par <strong>{METHODS.find(m => m.id === payment.declared_method)?.label ?? payment.declared_method}</strong></>}.
              Votre gestionnaire le validera dès réception, le statut passera alors à « Validé ».
            </p>
          </div>
        </div>
      </div>
    )
  } else {
    payBlock = (
      <>
        <div className="flex items-baseline justify-between mb-3">
          <p className="text-sm font-medium text-gray-700">Régler mon loyer</p>
          <p className="text-sm text-gray-500">
            {MONTHS[payment.period_month]} {payment.period_year} : <strong className="text-gray-900">{fmtEuro(due)}</strong>
          </p>
        </div>
        {payment.status === 'late' && (
          <div className="mb-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
            <AlertCircle size={14} /> Paiement en retard : réglez dès que possible.
          </div>
        )}

        {/* Modes de paiement */}
        <div className="space-y-2">
          {METHODS.map(m => {
            const Icon = m.icon
            const isSelected = method === m.id
            return (
              <button
                key={m.id}
                onClick={() => setMethod(isSelected ? null : m.id)}
                className="w-full flex items-center gap-4 p-4 rounded-xl border text-left transition-all"
                style={{ border: isSelected ? `2px solid ${m.color}` : '1.5px solid #E5E7EB', background: isSelected ? `${m.color}08` : '#FFFFFF' }}
              >
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${m.color}15` }}>
                  <Icon size={18} style={{ color: m.color }} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-900">{m.label}</p>
                  <p className="text-xs text-gray-500">{m.desc}</p>
                </div>
                {isSelected && (
                  <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: m.color }}>
                    <CheckCircle size={12} className="text-white" />
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {/* À la sélection d'un mode : infos + montant modifiable + déclaration */}
        {method && (
          <div className="mt-4 space-y-4">
            {method === 'virement' && (
              payee?.iban ? (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm">
                  <p className="font-semibold text-green-800 mb-2">Coordonnées bancaires pour le virement</p>
                  <div className="space-y-1 text-green-700 font-mono text-xs">
                    {payee.name && <p className="font-sans">Titulaire : {payee.name}</p>}
                    <p>IBAN : {payee.iban}</p>
                    {payee.bic && <p>BIC&nbsp;&nbsp;: {payee.bic}</p>}
                    <p className="font-sans text-green-600 mt-2">Référence : LOYER-{payment.period_month?.toString().padStart(2, '0')}-{payment.period_year}</p>
                  </div>
                </div>
              ) : (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                  <p className="font-semibold mb-1">Coordonnées bancaires non disponibles</p>
                  <p>Le RIB de votre bailleur n'est pas encore renseigné. Contactez votre gestionnaire.</p>
                </div>
              )
            )}
            {method === 'especes' && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800">
                <p className="font-semibold mb-1">Règlement en espèces auprès de :</p>
                <p className="font-mono text-xs">{payee?.name ?? 'votre gestionnaire'}</p>
                {payee?.address && <p className="mt-1 font-mono text-xs">{payee.address}</p>}
              </div>
            )}

            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <label className="text-sm font-medium text-gray-700">Montant que vous réglez</label>
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="number" min="0" step="0.01" value={amount}
                  onChange={e => setAmount(Number(e.target.value))}
                  className="w-44 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-500">€</span>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Montant dû : <strong>{fmtEuro(due)}</strong>. Vous pouvez régler un montant partiel (le solde restera dû) ou supérieur (avance en votre faveur).
              </p>
              {amount > 0 && amount < due && (
                <p className="text-xs text-amber-600 mt-1">Paiement partiel : il restera {fmtEuro(due - amount)} à régler.</p>
              )}
              {amount > due && (
                <p className="text-xs text-green-600 mt-1">Avance : {fmtEuro(amount - due)} en votre faveur.</p>
              )}
            </div>

            <button
              onClick={handleDeclare}
              disabled={isSending || !amount || amount <= 0}
              className="w-full py-3.5 rounded-xl text-sm font-semibold text-white disabled:opacity-40"
              style={{ background: '#0D2F5C' }}
            >
              {isSending ? 'Envoi…' : `Déclarer le paiement de ${fmtEuro(amount)}`}
            </button>
            <p className="text-xs text-gray-400 text-center">
              En déclarant, vous informez votre gestionnaire. Le règlement reste « en attente » jusqu'à sa validation.
            </p>
          </div>
        )}
      </>
    )
  }

  return (
    <div className="p-4 sm:p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Payer mon loyer</h1>
        <p className="text-gray-500 text-sm mt-1">Solde, historique et règlement de votre loyer</p>
      </div>

      {soldeCard}
      {historyTable}

      <div className="mt-8">
        {payBlock}
      </div>
    </div>
  )
}
