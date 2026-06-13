import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Building2, Banknote, AlertCircle } from 'lucide-react'
import { apiClient } from '@/api/client'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

const METHODS: Record<string, { icon: any; label: string; color: string }> = {
  virement: { icon: Building2, label: 'Virement bancaire', color: '#059669' },
  especes: { icon: Banknote, label: 'Espèces', color: '#DC2626' },
}

const MONTHS = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

export default function LocatairePayerForm() {
  const { method = '' } = useParams()
  const navigate = useNavigate()
  const cfg = METHODS[method]

  const [payment, setPayment] = useState<any>(null)
  const [payee, setPayee] = useState<{ name?: string; address?: string; iban?: string; bic?: string } | null>(null)
  const [amount, setAmount] = useState<number>(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)

  useEffect(() => {
    apiClient.get('/payments/locataire/current')
      .then(({ data }) => {
        setPayment(data.payment)
        setPayee(data.payee ?? null)
        if (data.payment) setAmount(Number(data.payment.balance ?? data.payment.amount_due) || 0)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const due = Number(payment?.balance ?? payment?.amount_due) || 0

  const handleDeclare = async () => {
    if (!payment || amount <= 0) return
    setIsSending(true)
    try {
      await apiClient.post('/payments/locataire/declare', { method, amount, payment_id: payment.id })
      navigate('/locataire/payer')
    } finally {
      setIsSending(false)
    }
  }

  const Back = (
    <button onClick={() => navigate('/locataire/payer')}
      className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-4">
      <ArrowLeft size={16} /> Retour
    </button>
  )

  if (isLoading) {
    return <div className="p-6 flex items-center justify-center h-48"><p className="text-gray-400 text-sm">Chargement…</p></div>
  }

  if (!cfg) {
    return (
      <div className="p-4 sm:p-6 max-w-2xl">
        {Back}
        <p className="text-gray-600">Mode de paiement inconnu.</p>
      </div>
    )
  }

  if (!payment || due <= 0.005) {
    return (
      <div className="p-4 sm:p-6 max-w-2xl">
        {Back}
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-gray-700 font-medium">Aucun loyer à régler</p>
          <p className="text-sm text-gray-400 mt-1">Vous êtes à jour dans vos paiements.</p>
        </div>
      </div>
    )
  }

  const Icon = cfg.icon

  return (
    <div className="p-4 sm:p-6 max-w-2xl">
      {Back}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${cfg.color}15` }}>
          <Icon size={20} style={{ color: cfg.color }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Régler par {cfg.label.toLowerCase()}</h1>
          <p className="text-gray-500 text-sm">{MONTHS[payment.period_month]} {payment.period_year} · {fmtEuro(due)} dû</p>
        </div>
      </div>

      {/* Coordonnées du bailleur selon le mode */}
      {method === 'virement' && (
        payee?.iban ? (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-5 text-sm">
            <p className="font-semibold text-green-800 mb-2">Coordonnées bancaires pour le virement</p>
            <div className="space-y-1 text-green-700 font-mono text-xs">
              {payee.name && <p className="font-sans">Titulaire : {payee.name}</p>}
              <p>IBAN : {payee.iban}</p>
              {payee.bic && <p>BIC&nbsp;&nbsp;: {payee.bic}</p>}
              <p className="font-sans text-green-600 mt-2">Référence : LOYER-{payment.period_month?.toString().padStart(2, '0')}-{payment.period_year}</p>
            </div>
          </div>
        ) : (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-5 text-sm text-amber-800">
            <p className="font-semibold mb-1">Coordonnées bancaires non disponibles</p>
            <p>Le RIB de votre bailleur n'est pas encore renseigné. Contactez votre gestionnaire.</p>
          </div>
        )
      )}
      {method === 'especes' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-5 text-sm text-red-800">
          <p className="font-semibold mb-1">Règlement en espèces auprès de :</p>
          <p className="font-mono text-xs">{payee?.name ?? 'votre gestionnaire'}</p>
          {payee?.address && <p className="mt-1 font-mono text-xs">{payee.address}</p>}
        </div>
      )}

      {/* Montant modifiable */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-5">
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

      {payment.status === 'late' && (
        <div className="mb-5 flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
          <AlertCircle size={14} /> Paiement en retard : réglez dès que possible.
        </div>
      )}

      <button
        onClick={handleDeclare}
        disabled={isSending || !amount || amount <= 0}
        className="w-full py-3.5 rounded-xl text-sm font-semibold text-white disabled:opacity-40"
        style={{ background: '#0D2F5C' }}
      >
        {isSending ? 'Envoi…' : `Déclarer le paiement de ${fmtEuro(amount)}`}
      </button>
      <p className="text-xs text-gray-400 text-center mt-2">
        En déclarant, vous informez votre gestionnaire. Le règlement reste « en attente » jusqu'à sa validation.
      </p>
    </div>
  )
}
