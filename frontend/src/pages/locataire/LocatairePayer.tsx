import { useState, useEffect } from 'react'
import { Building2, Banknote, CheckCircle, AlertCircle, Wallet } from 'lucide-react'
import { apiClient } from '@/api/client'
import { paymentsApi } from '@/api/payments'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { StatusBadge } from '@/components/common/StatusBadge'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

const METHODS = [
  {
    id: 'virement',
    icon: Building2,
    label: 'Virement bancaire',
    desc: 'SEPA, délai 1-2 jours',
    color: '#059669',
  },
  {
    id: 'especes',
    icon: Banknote,
    label: 'Espèces',
    desc: 'En agence ou à l\'accueil',
    color: '#DC2626',
  },
]

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: 'En attente',    color: '#D97706', bg: '#FEF3C7' },
  partial: { label: 'Partiel',       color: '#2563EB', bg: '#DBEAFE' },
  late:    { label: 'En retard',     color: '#DC2626', bg: '#FEE2E2' },
  paid:    { label: 'Payé',          color: '#059669', bg: '#D1FAE5' },
}

const MONTHS = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

export default function LocatairePayer() {
  const [payment, setPayment] = useState<any>(null)
  const [payee, setPayee] = useState<{ name?: string; address?: string; iban?: string; bic?: string } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [method, setMethod] = useState<string | null>(null)
  const [amount, setAmount] = useState<number>(0)
  const [step, setStep] = useState<'select' | 'confirm' | 'success'>('select')
  const [isSending, setIsSending] = useState(false)
  const [allPayments, setAllPayments] = useState<any[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])

  useEffect(() => {
    Promise.allSettled([
      apiClient.get('/payments/locataire/current'),
      paymentsApi.list({ limit: 120 }),
      apurementApi.mine(),
    ]).then(([cur, lst, pl]) => {
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
    }).finally(() => setIsLoading(false))
  }, [])

  // Solde actuel = cumul du reste à payer (loyers non soldés + échéances d'apurement
  // non réglées), tous mois confondus.
  const soldeActuel = Math.round((
    allPayments.filter((p: any) => p.status !== 'cancelled')
      .reduce((s: number, p: any) => s + (Number(p.balance ?? 0) || 0), 0)
    + plans.flatMap(pl => pl.installments).filter(i => !i.paid).reduce((s, i) => s + i.amount, 0)
  ) * 100) / 100

  // Historique : loyers + échéances d'apurement.
  const HIST_STATUS: Record<string, { label: string; variant: any }> = {
    paid: { label: 'Payé', variant: 'green' }, partial: { label: 'Partiel', variant: 'yellow' },
    pending: { label: 'En attente', variant: 'blue' }, late: { label: 'En retard', variant: 'red' },
    declared: { label: 'Déclaré', variant: 'yellow' }, cancelled: { label: 'Annulé', variant: 'gray' },
  }
  const todayIso = new Date().toISOString().slice(0, 10)
  const history = [
    ...allPayments.map((p: any) => ({
      key: `p-${p.id}`, date: p.payment_date, intitule: `Loyer · ${p.period_label}`,
      echeance: p.due_date, montant: p.amount_due ?? 0, status: p.status, sort: p.due_date || '',
    })),
    ...plans.flatMap(pl => pl.installments.map(i => ({
      key: `i-${pl.id}-${i.seq}`, date: i.paid ? (i.paid_date || i.due_date) : null,
      intitule: `Plan d'apurement · échéance ${i.seq}`, echeance: i.due_date, montant: i.amount,
      status: i.paid ? 'paid' : i.declared ? 'declared' : (i.due_date < todayIso ? 'late' : 'pending'),
      sort: i.due_date,
    }))),
  ].sort((a, b) => b.sort.localeCompare(a.sort))

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
                const st = HIST_STATUS[h.status] ?? { label: h.status, variant: 'gray' }
                return (
                  <tr key={h.key} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{h.date ? format(new Date(h.date), 'd MMM yyyy', { locale: fr }) : '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-800">{h.intitule}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{h.echeance ? format(new Date(h.echeance), 'd MMM yyyy', { locale: fr }) : '—'}</td>
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

  const handleDeclare = async () => {
    if (!method || !payment || amount <= 0) return
    setIsSending(true)
    try {
      await apiClient.post('/payments/locataire/declare', {
        method,
        amount,
        payment_id: payment.id,
      })
      setStep('success')
    } finally {
      setIsSending(false)
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-48">
        <p className="text-gray-400 text-sm">Chargement…</p>
      </div>
    )
  }

  if (!payment) {
    return (
      <div className="p-4 sm:p-6 max-w-2xl">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Payer mon loyer</h1>
        </div>
        {soldeCard}
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <CheckCircle size={36} className="mx-auto mb-2 text-green-400" />
          <p className="text-gray-700 font-medium">Aucun paiement en attente</p>
          <p className="text-sm text-gray-400 mt-1">Vous n'avez pas d'appel de loyer à régler actuellement.</p>
        </div>
        {historyTable}
      </div>
    )
  }

  const statusCfg = STATUS_LABELS[payment.status] ?? STATUS_LABELS.pending
  // « Loyer dû » = ce qu'il reste à payer après déduction de l'aide au logement (et acomptes).
  const due = Number(payment.balance ?? payment.amount_due) || 0

  if (step === 'success') {
    const selectedMethod = METHODS.find(m => m.id === method)
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Payer mon loyer</h1>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center max-w-md mx-auto">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={32} className="text-green-500" />
          </div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">Déclaration envoyée</h2>
          <p className="text-sm text-gray-500 mb-4">
            Votre déclaration de paiement par <strong>{selectedMethod?.label}</strong> a été transmise à votre gestionnaire.
            Il la validera dès réception du règlement.
          </p>
          <p className="text-xs text-gray-400">Montant déclaré : <strong>{fmtEuro(amount)}</strong></p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Payer mon loyer</h1>
        <p className="text-gray-500 text-sm mt-1">Choisissez votre mode de règlement</p>
      </div>

      {soldeCard}

      {/* Récapitulatif */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Loyer dû</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{fmtEuro(due)}</p>
            <p className="text-sm text-gray-500 mt-0.5">
              {MONTHS[payment.period_month]} {payment.period_year}
              {payment.due_date && ` · Échéance le ${format(new Date(payment.due_date), 'd MMMM', { locale: fr })}`}
            </p>
          </div>
          <span className="text-xs font-semibold px-3 py-1.5 rounded-full"
            style={{ color: statusCfg.color, background: statusCfg.bg }}>
            {statusCfg.label}
          </span>
        </div>
        {(payment.amount_charges > 0 || (payment.amount_apl ?? 0) > 0) && (
          <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-600">
            <span>Loyer nu</span>
            <span className="text-right font-medium">{fmtEuro(payment.amount_rent)}</span>
            {payment.amount_charges > 0 && <>
              <span>Charges</span>
              <span className="text-right font-medium">{fmtEuro(payment.amount_charges)}</span>
            </>}
            {payment.amount_apl > 0 && <>
              <span className="text-green-600">Aide personnelle au logement déduite</span>
              <span className="text-right font-medium text-green-600">− {fmtEuro(payment.amount_apl)}</span>
            </>}
            <span className="font-semibold text-gray-700 pt-1 border-t border-gray-100">Reste à payer</span>
            <span className="text-right font-bold text-gray-900 pt-1 border-t border-gray-100">{fmtEuro(due)}</span>
          </div>
        )}
        {payment.status === 'late' && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
            <AlertCircle size={14} />
            Paiement en retard : contactez votre gestionnaire si nécessaire.
          </div>
        )}
      </div>

      {step === 'select' && (
        <>
          <p className="text-sm font-medium text-gray-700 mb-3">Choisissez un mode de paiement</p>
          <div className="space-y-2 mb-6">
            {METHODS.map(m => {
              const Icon = m.icon
              const isSelected = method === m.id
              return (
                <button
                  key={m.id}
                  onClick={() => setMethod(m.id)}
                  className="w-full flex items-center gap-4 p-4 rounded-xl border text-left transition-all"
                  style={{
                    border: isSelected ? `2px solid ${m.color}` : '1.5px solid #E5E7EB',
                    background: isSelected ? `${m.color}08` : '#FFFFFF',
                  }}
                >
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: `${m.color}15` }}>
                    <Icon size={18} style={{ color: m.color }} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">{m.label}</p>
                    <p className="text-xs text-gray-500">{m.desc}</p>
                  </div>
                  {isSelected && (
                    <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ background: m.color }}>
                      <CheckCircle size={12} className="text-white" />
                    </div>
                  )}
                </button>
              )
            })}
          </div>

          {/* Informations contextuelles selon méthode */}
          {method === 'virement' && (
            payee?.iban ? (
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-5 text-sm">
                <p className="font-semibold text-green-800 mb-2">Coordonnées bancaires pour le virement</p>
                <div className="space-y-1 text-green-700 font-mono text-xs">
                  {payee.name && <p className="font-sans text-green-700">Titulaire : {payee.name}</p>}
                  <p>IBAN : {payee.iban}</p>
                  {payee.bic && <p>BIC&nbsp;&nbsp;: {payee.bic}</p>}
                  <p className="font-sans text-xs text-green-600 mt-2">Référence : LOYER-{payment.period_month?.toString().padStart(2,'0')}-{payment.period_year}</p>
                </div>
              </div>
            ) : (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-5 text-sm text-amber-800">
                <p className="font-semibold mb-1">Coordonnées bancaires non disponibles</p>
                <p>Le RIB de votre bailleur n'est pas encore renseigné. Contactez votre gestionnaire pour obtenir les coordonnées du virement.</p>
              </div>
            )
          )}
          {method === 'especes' && (
            payee?.name ? (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-5 text-sm text-red-800">
                <p className="font-semibold mb-1">Règlement en espèces auprès de :</p>
                <p className="font-mono text-xs">{payee.name}</p>
                {payee.address && (
                  <p className="mt-1 font-mono text-xs">{payee.address}</p>
                )}
              </div>
            ) : (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-5 text-sm text-red-800">
                <p className="font-semibold mb-1">Coordonnées non disponibles</p>
                <p>Les coordonnées de votre bailleur ne sont pas encore renseignées. Contactez votre gestionnaire.</p>
              </div>
            )
          )}

          {/* Montant à régler : modifiable (partiel ou avance) */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 mb-5">
            <label className="text-sm font-medium text-gray-700">Montant que vous réglez</label>
            <div className="mt-2 flex items-center gap-2">
              <input
                type="number" min="0" step="0.01"
                value={amount}
                onChange={e => setAmount(Number(e.target.value))}
                className="w-44 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-500">€</span>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Montant dû : <strong>{fmtEuro(due)}</strong>. Vous pouvez régler un
              montant différent : partiel (le solde restera dû) ou supérieur (avance en votre faveur).
            </p>
            {amount > 0 && amount < due && (
              <p className="text-xs text-amber-600 mt-1">
                Paiement partiel : il restera {fmtEuro(due - amount)} à régler.
              </p>
            )}
            {amount > due && (
              <p className="text-xs text-green-600 mt-1">
                Avance : {fmtEuro(amount - due)} en votre faveur.
              </p>
            )}
          </div>

          <button
            onClick={() => setStep('confirm')}
            disabled={!method || !amount || amount <= 0}
            className="w-full py-3.5 rounded-xl text-sm font-semibold text-white disabled:opacity-40"
            style={{ background: '#0D2F5C' }}
          >
            Continuer →
          </button>
        </>
      )}

      {step === 'confirm' && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Confirmer la déclaration</h3>
          <div className="space-y-3 text-sm mb-6">
            <div className="flex justify-between">
              <span className="text-gray-500">Montant déclaré</span>
              <span className="font-semibold text-gray-900">{fmtEuro(amount)}</span>
            </div>
            {amount !== due && (
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">Montant dû</span>
                <span className="text-gray-400">{fmtEuro(due)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-500">Période</span>
              <span className="font-medium">{MONTHS[payment.period_month]} {payment.period_year}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Mode de paiement</span>
              <span className="font-medium">{METHODS.find(m => m.id === method)?.label}</span>
            </div>
          </div>
          <p className="text-xs text-gray-400 mb-5">
            En confirmant, vous déclarez avoir initié ce paiement. Votre gestionnaire recevra une notification et mettra à jour votre dossier à réception.
          </p>
          <div className="flex gap-3">
            <button onClick={() => setStep('select')}
              className="flex-1 py-3 rounded-xl text-sm border border-gray-200 text-gray-600 hover:bg-gray-50">
              Modifier
            </button>
            <button onClick={handleDeclare} disabled={isSending}
              className="flex-1 py-3 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
              style={{ background: '#0D2F5C' }}>
              {isSending ? 'Envoi…' : 'Confirmer le paiement'}
            </button>
          </div>
        </div>
      )}

      {historyTable}
    </div>
  )
}
