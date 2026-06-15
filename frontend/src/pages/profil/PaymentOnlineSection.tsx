import { useEffect, useState } from 'react'
import { CreditCard, Save, Copy, Check, Plug } from 'lucide-react'
import { onlinePaymentsApi, type PaymentConfig } from '@/api/onlinePayments'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

const inp = 'w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

/** « Mes informations » (gestionnaire) : configuration du paiement du loyer par
 *  carte. Les clés sont propres au compte ; les secrets ne sont jamais réaffichés
 *  (seul l'état « renseigné » est connu) : laissez vide pour conserver l'existant. */
export default function PaymentOnlineSection() {
  const [cfg, setCfg] = useState<PaymentConfig | null>(null)
  const [provider, setProvider] = useState<'stripe' | 'sumup'>('stripe')
  const [enabled, setEnabled] = useState(false)
  const [currency, setCurrency] = useState('EUR')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [copied, setCopied] = useState(false)

  // Champs (secrets : vides au chargement, saisis seulement pour modifier).
  const [stripeSecret, setStripeSecret] = useState('')
  const [stripePub, setStripePub] = useState('')
  const [stripeWh, setStripeWh] = useState('')
  const [sumupApi, setSumupApi] = useState('')
  const [sumupMerchant, setSumupMerchant] = useState('')

  useEffect(() => {
    onlinePaymentsApi.getConfig().then(({ data }) => {
      setCfg(data)
      setProvider(data.payment_provider || 'stripe')
      setEnabled(data.card_payments_enabled)
      setCurrency(data.payment_currency || 'EUR')
      setStripePub(data.stripe.publishable_key || '')
      setSumupMerchant(data.sumup.merchant_code || '')
    }).catch(() => { /* non-gestionnaire ou erreur : section masquée par le parent */ })
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        payment_provider: provider,
        card_payments_enabled: enabled,
        payment_currency: currency,
        stripe_publishable_key: stripePub,
        sumup_merchant_code: sumupMerchant,
      }
      if (stripeSecret.trim()) payload.stripe_secret_key = stripeSecret.trim()
      if (stripeWh.trim()) payload.stripe_webhook_secret = stripeWh.trim()
      if (sumupApi.trim()) payload.sumup_api_key = sumupApi.trim()
      const { data } = await onlinePaymentsApi.putConfig(payload)
      setCfg(data)
      setStripeSecret(''); setStripeWh(''); setSumupApi('')
      toast.success('Configuration de paiement enregistrée')
    } catch (e) {
      toast.error(getErrorMessage(e, "Échec de l'enregistrement"))
    } finally {
      setSaving(false)
    }
  }

  const testConnection = async () => {
    setTesting(true)
    try {
      const { data } = await onlinePaymentsApi.testConfig()
      if (data.ok) toast.success(data.detail)
      else toast.error(data.detail)
    } catch (e) {
      toast.error(getErrorMessage(e, 'Test de connexion impossible'))
    } finally {
      setTesting(false)
    }
  }

  if (!cfg) return null

  const setBadge = (ok: boolean) =>
    ok ? <span className="text-[11px] text-green-600">déjà renseigné</span>
       : <span className="text-[11px] text-gray-400">non renseigné</span>

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 mt-5">
      <div className="flex items-center gap-2">
        <CreditCard size={16} className="text-blue-600" />
        <h2 className="text-sm font-semibold text-gray-900">Paiement du loyer par carte</h2>
      </div>
      <p className="text-xs text-gray-500 -mt-2">
        Proposez à vos locataires le règlement par carte bancaire. Renseignez vos propres
        clés Stripe ou SumUp : elles restent privées et ne servent qu'à vos encaissements.
        Tant que ce n'est pas activé, le paiement par carte reste grisé chez vos locataires.
      </p>

      {/* Activation */}
      <label className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 cursor-pointer">
        <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
        <span className="text-xs text-gray-700">
          <span className="font-medium text-gray-800">Activer le paiement par carte</span>
          <span className="block text-[11px] text-gray-500 mt-0.5">
            Vos locataires verront le bouton « Carte bancaire » dans leur espace de paiement.
          </span>
        </span>
      </label>

      {/* Prestataire */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1.5">Prestataire</label>
        <div className="grid grid-cols-2 gap-2">
          {(['stripe', 'sumup'] as const).map(p => (
            <button key={p} type="button" onClick={() => setProvider(p)}
              className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                provider === p ? 'border-blue-500 bg-blue-50 text-blue-900' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
              {p === 'stripe' ? 'Stripe' : 'SumUp'}
            </button>
          ))}
        </div>
      </div>

      {/* Devise (configurable) */}
      <div className="w-32">
        <label className="block text-xs font-medium text-gray-600 mb-1">Devise</label>
        <input type="text" className={inp} value={currency} maxLength={3}
          onChange={e => setCurrency(e.target.value.toUpperCase())} placeholder="EUR" />
      </div>

      {provider === 'stripe' ? (
        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-medium text-gray-600">Clé secrète Stripe (sk_…)</label>
              {setBadge(cfg.stripe.secret_key_set)}
            </div>
            <input type="password" autoComplete="off" className={inp} value={stripeSecret}
              onChange={e => setStripeSecret(e.target.value)}
              placeholder={cfg.stripe.secret_key_set ? '•••••••• (laisser vide pour conserver)' : 'sk_live_…'} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Clé publique Stripe (pk_…)</label>
            <input type="text" className={inp} value={stripePub}
              onChange={e => setStripePub(e.target.value)} placeholder="pk_live_…" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-medium text-gray-600">Secret de signature du webhook (whsec_…)</label>
              {setBadge(cfg.stripe.webhook_secret_set)}
            </div>
            <input type="password" autoComplete="off" className={inp} value={stripeWh}
              onChange={e => setStripeWh(e.target.value)}
              placeholder={cfg.stripe.webhook_secret_set ? '•••••••• (laisser vide pour conserver)' : 'whsec_…'} />
            <div className="mt-2 flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
              <span className="text-[11px] text-gray-500 break-all flex-1">
                URL du webhook à déclarer dans Stripe (événement <b>checkout.session.completed</b>) :<br />
                <code className="text-gray-700">{cfg.stripe.webhook_url}</code>
              </span>
              <button type="button" title="Copier"
                onClick={() => { navigator.clipboard.writeText(cfg.stripe.webhook_url); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
                className="p-1.5 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50">
                {copied ? <Check size={14} /> : <Copy size={14} />}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-medium text-gray-600">Clé API SumUp (secret)</label>
              {setBadge(cfg.sumup.api_key_set)}
            </div>
            <input type="password" autoComplete="off" className={inp} value={sumupApi}
              onChange={e => setSumupApi(e.target.value)}
              placeholder={cfg.sumup.api_key_set ? '•••••••• (laisser vide pour conserver)' : 'sup_sk_…'} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Merchant code SumUp</label>
            <input type="text" className={inp} value={sumupMerchant}
              onChange={e => setSumupMerchant(e.target.value)} placeholder="MXXXXXXX" />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 pt-1">
        <button onClick={testConnection} disabled={testing}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 disabled:opacity-60"
          title="Vérifie vos clés auprès du prestataire, sans paiement réel (enregistrez d'abord)">
          <Plug size={15} /> {testing ? 'Test…' : 'Tester la connexion'}
        </button>
        <button onClick={save} disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
          <Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </div>
    </div>
  )
}
