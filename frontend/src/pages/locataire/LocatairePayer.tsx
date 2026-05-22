import { useState, useEffect } from 'react'
import { CreditCard, Building2, RefreshCw, FileText, Banknote, CheckCircle, AlertCircle } from 'lucide-react'
import { apiClient } from '@/api/client'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

const METHODS = [
  {
    id: 'carte',
    icon: CreditCard,
    label: 'Carte bancaire',
    desc: 'Visa, Mastercard, CB',
    color: '#2563EB',
  },
  {
    id: 'virement',
    icon: Building2,
    label: 'Virement bancaire',
    desc: 'SEPA, délai 1-2 jours',
    color: '#059669',
  },
  {
    id: 'prelevement',
    icon: RefreshCw,
    label: 'Prélèvement automatique',
    desc: 'Mandat SEPA',
    color: '#7C3AED',
  },
  {
    id: 'cheque',
    icon: FileText,
    label: 'Chèque',
    desc: 'À envoyer par courrier',
    color: '#D97706',
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
  const [isLoading, setIsLoading] = useState(true)
  const [method, setMethod] = useState<string | null>(null)
  const [step, setStep] = useState<'select' | 'confirm' | 'success'>('select')
  const [isSending, setIsSending] = useState(false)

  useEffect(() => {
    apiClient.get('/payments/locataire/current')
      .then(r => setPayment(r.data.payment))
      .catch(() => { })
      .finally(() => setIsLoading(false))
  }, [])

  const handleDeclare = async () => {
    if (!method || !payment) return
    setIsSending(true)
    try {
      await apiClient.post('/payments/locataire/declare', {
        method,
        amount: payment.amount_due,
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
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Payer mon loyer</h1>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <CheckCircle size={40} className="mx-auto mb-3 text-green-400" />
          <p className="text-gray-700 font-medium">Aucun paiement en attente</p>
          <p className="text-sm text-gray-400 mt-1">Vous êtes à jour dans vos règlements.</p>
        </div>
      </div>
    )
  }

  const statusCfg = STATUS_LABELS[payment.status] ?? STATUS_LABELS.pending

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
          <p className="text-xs text-gray-400">Montant déclaré : <strong>{fmtEuro(payment.amount_due)}</strong></p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Payer mon loyer</h1>
        <p className="text-gray-500 text-sm mt-1">Choisissez votre mode de règlement</p>
      </div>

      {/* Récapitulatif */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Loyer dû</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{fmtEuro(payment.amount_due)}</p>
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
        {payment.amount_due !== payment.amount_rent && (
          <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 gap-2 text-sm text-gray-600">
            <span>Loyer nu</span>
            <span className="text-right font-medium">{fmtEuro(payment.amount_rent)}</span>
            {payment.amount_charges > 0 && <>
              <span>Charges</span>
              <span className="text-right font-medium">{fmtEuro(payment.amount_charges)}</span>
            </>}
            {payment.amount_apl > 0 && <>
              <span className="text-green-600">APL déduit</span>
              <span className="text-right font-medium text-green-600">− {fmtEuro(payment.amount_apl)}</span>
            </>}
          </div>
        )}
        {payment.status === 'late' && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
            <AlertCircle size={14} />
            Paiement en retard — contactez votre gestionnaire si nécessaire.
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
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-5 text-sm">
              <p className="font-semibold text-green-800 mb-2">Coordonnées bancaires pour le virement</p>
              <div className="space-y-1 text-green-700 font-mono text-xs">
                <p>IBAN : FR76 3000 4028 3798 7654 3210 943</p>
                <p>BIC  : BNPAFRPPXXX</p>
                <p className="font-sans text-xs text-green-600 mt-2">Référence : LOYER-{payment.period_month?.toString().padStart(2,'0')}-{payment.period_year}</p>
              </div>
            </div>
          )}
          {method === 'cheque' && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-5 text-sm text-amber-800">
              <p className="font-semibold mb-1">Envoyez votre chèque à l'ordre de :</p>
              <p className="font-mono text-xs">LeComptoirImmo — 12 rue de la Gestion, 75001 Paris</p>
            </div>
          )}
          {method === 'especes' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-5 text-sm text-red-800">
              <p className="font-semibold mb-1">Règlement en espèces à l'accueil :</p>
              <p>Du lundi au vendredi, 9h–17h</p>
              <p className="font-mono text-xs mt-1">12 rue de la Gestion, 75001 Paris</p>
            </div>
          )}
          {method === 'carte' && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-5 text-sm text-blue-800">
              <p className="font-semibold mb-1">Paiement par carte sécurisé</p>
              <p>En cliquant sur "Confirmer", votre gestionnaire sera notifié et vous contactera pour procéder au paiement.</p>
            </div>
          )}
          {method === 'prelevement' && (
            <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-5 text-sm text-purple-800">
              <p className="font-semibold mb-1">Prélèvement automatique</p>
              <p>En confirmant, vous signalez à votre gestionnaire votre souhait de mettre en place un mandat SEPA. Il vous contactera pour la mise en place.</p>
            </div>
          )}

          <button
            onClick={() => setStep('confirm')}
            disabled={!method}
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
              <span className="text-gray-500">Montant</span>
              <span className="font-semibold text-gray-900">{fmtEuro(payment.amount_due)}</span>
            </div>
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
    </div>
  )
}
