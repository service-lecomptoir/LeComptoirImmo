import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, ShieldCheck } from 'lucide-react'
import { onlinePaymentsApi } from '@/api/onlinePayments'
import { toast } from '@/store/toast'

const SUMUP_SDK = 'https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js'
const fmtEuro = (n?: number) =>
  (n ?? 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

/** Paiement du loyer par carte via SumUp : monte le widget carte SumUp sur le
 *  checkout créé côté serveur, puis confirme le règlement (vérification serveur). */
export default function LocataireCarteSumup() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state as { checkoutId?: string; amount?: number } | null) || {}
  const checkoutId = state.checkoutId
  const mountedRef = useRef(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!checkoutId) { setError('Paiement introuvable. Relancez le règlement.'); return }
    if (mountedRef.current) return
    mountedRef.current = true

    const confirm = async () => {
      try {
        const { data } = await onlinePaymentsApi.sumupConfirm(checkoutId)
        if (data.status === 'paid') {
          toast.success('Paiement par carte confirmé. Votre loyer est enregistré.')
          navigate('/locataire/payer?card=success', { replace: true })
        } else {
          setError('Le paiement n\'a pas abouti. Vous pouvez réessayer.')
        }
      } catch {
        setError('Impossible de confirmer le paiement. Contactez votre gestionnaire si le montant a été débité.')
      }
    }

    const mount = () => {
      const SumUpCard = (window as any).SumUpCard
      if (!SumUpCard) { setError('Le module de paiement SumUp n\'a pas pu être chargé.'); return }
      SumUpCard.mount({
        id: 'sumup-card',
        checkoutId,
        locale: 'fr-FR',
        onResponse: (type: string) => {
          if (type === 'success') confirm()
          else if (type === 'error' || type === 'fail') setError('Le paiement a échoué. Vérifiez vos informations et réessayez.')
        },
      })
    }

    const existing = document.querySelector(`script[src="${SUMUP_SDK}"]`)
    if (existing && (window as any).SumUpCard) { mount(); return }
    const s = document.createElement('script')
    s.src = SUMUP_SDK
    s.async = true
    s.onload = mount
    s.onerror = () => setError('Le module de paiement SumUp n\'a pas pu être chargé.')
    document.body.appendChild(s)
  }, [checkoutId, navigate])

  return (
    <div className="p-4 sm:p-6 max-w-md mx-auto">
      <button onClick={() => navigate('/locataire/payer')}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={16} /> Retour
      </button>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck size={18} className="text-emerald-600" />
          <h1 className="text-lg font-bold text-gray-900">Paiement par carte</h1>
        </div>
        {state.amount != null && (
          <p className="text-sm text-gray-500 mb-4">Montant à régler : <strong>{fmtEuro(state.amount)}</strong></p>
        )}

        {error ? (
          <div className="px-3 py-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        ) : (
          <div id="sumup-card" />
        )}

        <p className="mt-4 text-xs text-gray-400">
          Paiement sécurisé : vos données carte sont traitées par SumUp, jamais par Le Comptoir Immo.
        </p>
      </div>
    </div>
  )
}
