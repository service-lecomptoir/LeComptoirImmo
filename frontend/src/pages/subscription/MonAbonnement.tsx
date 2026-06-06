import { useEffect, useState } from 'react'
import { CreditCard, Building2, CheckCircle, XCircle, AlertTriangle, Package, FileDown, Receipt, ListChecks, Check } from 'lucide-react'
import { subscriptionApi, type SubscriptionInfo, type SubscriptionInvoice, type BillingStatus, type AvailablePlan, type StripePayment } from '@/api/subscription'
import { FEATURE_LABELS } from '@/lib/features'
import { downloadBlob } from '@/utils/download'
import { toast } from '@/store/toast'

const FEATURE_ORDER = Object.keys(FEATURE_LABELS)

function ProgressBar({ value, max }: { value: number; max: number | null }) {
  if (max === null) {
    return (
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div className="bg-green-500 h-2 rounded-full w-full" />
      </div>
    )
  }
  const pct = Math.min(100, Math.round((value / max) * 100))
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-orange-400' : 'bg-blue-500'
  return (
    <div className="w-full bg-gray-100 rounded-full h-2">
      <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function MonAbonnement() {
  const [info, setInfo] = useState<SubscriptionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showResiliation, setShowResiliation] = useState(false)
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [resiliationSent, setResiliationSent] = useState(false)
  const [resiliationError, setResiliationError] = useState<string | null>(null)
  const [invoices, setInvoices] = useState<SubscriptionInvoice[]>([])
  const [billing, setBilling] = useState<BillingStatus | null>(null)
  const [billingBusy, setBillingBusy] = useState(false)
  const [plans, setPlans] = useState<AvailablePlan[]>([])
  const [payments, setPayments] = useState<StripePayment[]>([])
  const [newPlanId, setNewPlanId] = useState('')
  const [changingPlan, setChangingPlan] = useState(false)

  const changePlan = async () => {
    if (!newPlanId) return
    const target = plans.find(p => p.id === newPlanId)
    if (!confirm(`Changer pour le plan « ${target?.name} » (${target?.monthly_price} €/mois) ?\n\nLe montant sera ajusté au prorata sur votre prochaine facture.`)) return
    setChangingPlan(true)
    try {
      const { data } = await subscriptionApi.changePlan(newPlanId)
      toast.success(`Plan changé pour « ${data.plan_name} ». L'ajustement au prorata apparaîtra sur votre prochaine facture.`)
      setNewPlanId('')
      const [b] = await Promise.all([subscriptionApi.billing()])
      setBilling(b.data)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Changement de plan impossible')
    } finally {
      setChangingPlan(false)
    }
  }

  const startCheckout = async () => {
    setBillingBusy(true)
    try {
      const { data } = await subscriptionApi.checkout()
      window.location.href = data.url
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Impossible de démarrer le paiement')
      setBillingBusy(false)
    }
  }

  const openPortal = async () => {
    setBillingBusy(true)
    try {
      const { data } = await subscriptionApi.portal()
      window.location.href = data.url
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Impossible d'ouvrir le portail")
      setBillingBusy(false)
    }
  }

  const downloadInvoice = async (inv: SubscriptionInvoice) => {
    try {
      const res = await subscriptionApi.downloadInvoice(inv.id)
      downloadBlob(res.data as Blob, `facture-${inv.period_year}-${String(inv.period_month).padStart(2, '0')}.pdf`)
    } catch {
      toast.error('Téléchargement de la facture impossible')
    }
  }

  const submitResiliation = async () => {
    if (!reason.trim()) return
    setSubmitting(true)
    setResiliationError(null)
    try {
      await subscriptionApi.requestResiliation(reason.trim())
      setResiliationSent(true)
      setShowResiliation(false)
      setReason('')
      toast.success('Demande de résiliation envoyée')
    } catch (e: any) {
      setResiliationError(e?.response?.data?.detail || "Erreur lors de l'envoi de la demande")
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    subscriptionApi.get()
      .then(r => setInfo(r.data))
      .catch(e => setError(e.response?.data?.detail ?? 'Erreur lors du chargement'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    subscriptionApi.invoices().then(r => setInvoices(r.data)).catch(() => {})
    subscriptionApi.billing().then(r => setBilling(r.data)).catch(() => {})
    subscriptionApi.availablePlans().then(r => setPlans(r.data)).catch(() => {})
    subscriptionApi.payments().then(r => setPayments(r.data)).catch(() => {})
  }, [])

  // Retour de Stripe Checkout (?paiement=succes|annule)
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get('paiement')
    if (p === 'succes') toast.success('Paiement enregistré. Merci ! Votre abonnement est actif.')
    else if (p === 'annule') toast.info?.('Paiement annulé.')
    if (p) window.history.replaceState({}, '', window.location.pathname)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="text-red-500 shrink-0" size={20} />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      </div>
    )
  }

  const blocked = info?.is_blocked ?? false
  const noLicense = !info?.plan_name && blocked

  return (
    <div className="p-4 sm:p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mon abonnement</h1>
        <p className="text-gray-500 text-sm mt-1">Votre licence Alice et l'utilisation de votre compte</p>
      </div>

      {/* Status badge */}
      {blocked ? (
        <div className={`rounded-xl border p-4 flex items-center gap-3 ${noLicense ? 'bg-orange-50 border-orange-200' : 'bg-red-50 border-red-200'}`}>
          <XCircle className={noLicense ? 'text-orange-500' : 'text-red-500'} size={22} />
          <div>
            <p className={`font-semibold text-sm ${noLicense ? 'text-orange-800' : 'text-red-800'}`}>
              {noLicense ? 'Aucune licence associée' : 'Compte suspendu'}
            </p>
            <p className={`text-xs mt-0.5 ${noLicense ? 'text-orange-600' : 'text-red-600'}`}>
              {noLicense
                ? "Aucune licence Alice n'est liée à votre compte. Contactez votre administrateur."
                : 'Votre compte a été suspendu. Contactez votre administrateur Alice.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 flex items-center gap-3">
          <CheckCircle className="text-green-500" size={22} />
          <p className="font-semibold text-sm text-green-800">Compte actif</p>
        </div>
      )}

      {/* Paiement de l'abonnement (Stripe — carte / prélèvement SEPA) */}
      {billing?.stripe_enabled && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center gap-2 mb-3">
            <CreditCard size={18} className="text-blue-600" />
            <h2 className="text-sm font-semibold text-gray-900">Paiement de l'abonnement</h2>
          </div>
          {billing.has_subscription ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  billing.status === 'active' || billing.status === 'trialing'
                    ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                  {billing.status === 'active' ? 'Abonnement actif'
                    : billing.status === 'trialing' ? 'Période d\'essai'
                    : billing.status === 'past_due' ? 'Paiement en retard'
                    : billing.status === 'unpaid' ? 'Impayé'
                    : billing.status === 'canceled' ? 'Annulé' : (billing.status || '—')}
                </span>
                {billing.payment_method_type && (
                  <span className="text-gray-500 text-xs">
                    {billing.payment_method_type === 'sepa_debit' ? 'Prélèvement SEPA' : 'Carte bancaire'}
                  </span>
                )}
              </div>
              {billing.current_period_end && (
                <p className="text-xs text-gray-500">
                  Prochaine échéance : {new Date(billing.current_period_end).toLocaleDateString('fr-FR')}
                </p>
              )}
              <button onClick={openPortal} disabled={billingBusy}
                className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-60">
                {billingBusy ? 'Ouverture…' : 'Gérer mon abonnement'}
              </button>

              {plans.filter(p => p.name !== billing.plan_name).length > 0 && (
                <div className="pt-3 mt-1 border-t border-gray-100">
                  <p className="text-xs font-medium text-gray-600 mb-2">Changer de plan (ajusté au prorata)</p>
                  <div className="flex flex-wrap gap-2">
                    <select value={newPlanId} onChange={e => setNewPlanId(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                      <option value="">Choisir un plan…</option>
                      {plans.filter(p => p.name !== billing.plan_name).map(p => (
                        <option key={p.id} value={p.id}>{p.name} — {p.monthly_price} €/mois</option>
                      ))}
                    </select>
                    <button onClick={changePlan} disabled={!newPlanId || changingPlan}
                      className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                      {changingPlan ? 'Changement…' : 'Changer'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                Réglez votre abonnement en ligne par <b>carte bancaire</b> ou <b>prélèvement SEPA</b>.
                Le paiement est ensuite automatique chaque mois (résiliable à tout moment).
              </p>
              <button onClick={startCheckout} disabled={billingBusy}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
                <CreditCard size={15} /> {billingBusy ? 'Redirection…' : "Payer / activer le prélèvement"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Historique des paiements (Stripe) */}
      {payments.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center gap-2 mb-3">
            <Receipt size={18} className="text-blue-600" />
            <h2 className="text-sm font-semibold text-gray-900">Historique des paiements</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {payments.map(p => (
              <div key={p.id} className="flex items-center justify-between py-2.5 text-sm">
                <div>
                  <span className="text-gray-800">
                    {new Date(p.created * 1000).toLocaleDateString('fr-FR')}
                  </span>
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-xs font-medium ${
                    p.status === 'paid' ? 'bg-green-100 text-green-700'
                      : p.status === 'open' ? 'bg-amber-100 text-amber-700'
                      : 'bg-gray-100 text-gray-600'}`}>
                    {p.status === 'paid' ? 'Payé' : p.status === 'open' ? 'À payer'
                      : p.status === 'void' ? 'Annulé' : p.status}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-medium text-gray-900">
                    {p.amount.toFixed(2)} {(p.currency || 'eur').toUpperCase()}
                  </span>
                  {p.hosted_invoice_url && (
                    <a href={p.hosted_invoice_url} target="_blank" rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-700 text-xs font-medium inline-flex items-center gap-1">
                      <FileDown size={13} /> Reçu
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Résiliation programmée — décompte */}
      {info?.access_until && !blocked && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-center gap-3">
          <AlertTriangle className="text-amber-500 shrink-0" size={22} />
          <div>
            <p className="font-semibold text-sm text-amber-800">Résiliation programmée</p>
            <p className="text-xs text-amber-700 mt-0.5">
              Votre accès est maintenu jusqu'au {new Date(info.access_until).toLocaleDateString('fr-FR')}
              {info.resiliation_days_remaining != null &&
                ` — ${info.resiliation_days_remaining} jour${info.resiliation_days_remaining > 1 ? 's' : ''} restant${info.resiliation_days_remaining > 1 ? 's' : ''}`}.
            </p>
          </div>
        </div>
      )}

      {/* Plan card */}
      <div className="bg-white rounded-xl border divide-y">
        <div className="px-5 py-4 flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center">
            <Package className="text-blue-600" size={18} />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Plan</p>
            <p className="text-gray-900 font-semibold">
              {info?.plan_name ?? <span className="text-gray-400 italic">Aucun plan assigné</span>}
            </p>
          </div>
        </div>

        <div className="px-5 py-4 flex items-center gap-3">
          <div className="w-9 h-9 bg-indigo-50 rounded-lg flex items-center justify-center">
            <CreditCard className="text-indigo-600" size={18} />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Statut</p>
            <p className={`font-semibold ${blocked ? 'text-red-600' : 'text-green-600'}`}>
              {blocked ? 'Suspendu' : 'Actif'}
            </p>
          </div>
        </div>
      </div>

      {/* Property usage card */}
      <div className="bg-white rounded-xl border p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Building2 className="text-gray-500" size={18} />
          <h2 className="font-semibold text-gray-800">Utilisation des biens</h2>
        </div>

        <div>
          <div className="flex justify-between items-end mb-2">
            <span className="text-sm text-gray-600">Biens créés</span>
            <span className="text-sm font-semibold text-gray-900">
              {info?.property_count ?? 0}
              {info?.property_limit != null ? ` / ${info.property_limit}` : ' / Illimité'}
            </span>
          </div>
          <ProgressBar value={info?.property_count ?? 0} max={info?.property_limit ?? null} />
          {info?.property_limit != null && (
            <p className="text-xs text-gray-400 mt-1.5">
              {info.property_limit - (info.property_count ?? 0)} emplacement{(info.property_limit - (info.property_count ?? 0)) > 1 ? 's' : ''} restant{(info.property_limit - (info.property_count ?? 0)) > 1 ? 's' : ''}
            </p>
          )}
          {info?.property_limit === null && (
            <p className="text-xs text-gray-400 mt-1.5">Capacité illimitée incluse dans votre plan</p>
          )}
        </div>

        {!info?.can_create_property && !blocked && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <p className="text-xs text-orange-700 font-medium">
              Limite atteinte — vous ne pouvez plus créer de nouveaux biens. Contactez votre administrateur pour upgrader votre plan.
            </p>
          </div>
        )}
      </div>

      {/* Fonctionnalités incluses */}
      {info?.plan_name && !noLicense && (() => {
        const isAll = info.features == null || info.features.length >= FEATURE_ORDER.length
        const included = info.features == null ? FEATURE_ORDER : FEATURE_ORDER.filter(k => info.features!.includes(k))
        return (
          <div className="bg-white rounded-xl border p-5 space-y-3">
            <div className="flex items-center gap-2">
              <ListChecks className="text-gray-500" size={18} />
              <h2 className="font-semibold text-gray-800">Fonctionnalités incluses</h2>
            </div>
            {isAll ? (
              <p className="text-sm text-gray-600 flex items-center gap-2">
                <Check size={16} className="text-green-600 shrink-0" /> Toutes les fonctionnalités sont incluses dans votre plan.
              </p>
            ) : included.length === 0 ? (
              <p className="text-sm text-gray-400">Aucune fonctionnalité activée pour ce plan.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2">
                {included.map(k => (
                  <span key={k} className="flex items-center gap-2 text-sm text-gray-700">
                    <Check size={15} className="text-green-600 shrink-0" /> {FEATURE_LABELS[k]}
                  </span>
                ))}
              </div>
            )}
          </div>
        )
      })()}

      {/* Mes factures */}
      {invoices.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Receipt className="text-gray-500" size={18} />
            <h2 className="font-semibold text-gray-800">Mes factures</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {invoices.map(inv => (
              <div key={inv.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {String(inv.period_month).padStart(2, '0')}/{inv.period_year}
                    {inv.plan_name ? ` · ${inv.plan_name}` : ''}
                  </p>
                  <p className="text-xs text-gray-500 flex items-center gap-2 mt-0.5">
                    <span>{inv.amount.toFixed(2)} €</span>
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${inv.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                      {inv.status === 'paid' ? 'Payée' : 'À payer'}
                    </span>
                  </p>
                </div>
                <button
                  onClick={() => downloadInvoice(inv)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors shrink-0"
                >
                  <FileDown size={15} /> PDF
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Résiliation */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 className="font-semibold text-gray-800">Résilier mon abonnement</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Vous souhaitez mettre fin à votre abonnement Le Comptoir Immo ? Envoyez-nous une demande de
          résiliation : notre équipe la traitera et reviendra vers vous. Votre accès reste actif
          jusqu'à la confirmation de la résiliation.
        </p>

        {resiliationSent ? (
          <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
            <CheckCircle size={16} className="shrink-0" />
            Votre demande de résiliation a bien été transmise. Notre équipe vous recontactera.
          </div>
        ) : !showResiliation ? (
          <button
            onClick={() => setShowResiliation(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-red-300 text-red-600 bg-white hover:bg-red-50 transition-colors"
          >
            Mettre fin à mon abonnement
          </button>
        ) : (
          <div className="space-y-3">
            <label className="block text-xs font-medium text-gray-600">
              Pour nous aider à nous améliorer, indiquez la raison de votre départ
            </label>
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              rows={4}
              placeholder="Expliquez les raisons de votre résiliation…"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-300 resize-none"
            />
            {resiliationError && <p className="text-xs text-red-600">{resiliationError}</p>}
            <div className="flex items-center gap-2">
              <button
                onClick={submitResiliation}
                disabled={submitting || !reason.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? 'Envoi…' : 'Confirmer la demande'}
              </button>
              <button
                onClick={() => { setShowResiliation(false); setReason(''); setResiliationError(null) }}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 text-center">
        Géré par Alice — pour toute modification, contactez votre administrateur.
      </p>
    </div>
  )
}
