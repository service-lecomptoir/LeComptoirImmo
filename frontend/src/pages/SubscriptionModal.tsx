import { useState, useEffect } from 'react'
import { Button } from '@/components/ui'
import { getErrorMessage } from '@/utils/errors'
import { X, Send, CheckCircle, Check } from 'lucide-react'
import { apiClient } from '@/api/client'
import { publicPlansApi, type PublicPlan } from '@/api/publicPlans'
import SiretInput from '@/components/common/SiretInput'

interface Props {
  open: boolean
  onClose: () => void
  /** Plan pré-sélectionné (clic sur une carte de tarification). */
  initialPlanId?: string
}

/** Demande de souscription / démo — page d'accueil. Alimente Alice (lead à traiter). */
export default function SubscriptionModal({ open, onClose, initialPlanId }: Props) {
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', phone: '', company: '', siret: '', message: '' })
  // Type de demandeur : particulier (prénom/nom) ou société (raison sociale + SIRET).
  const [kind, setKind] = useState<'personne' | 'entreprise'>('personne')
  const [plans, setPlans] = useState<PublicPlan[]>([])
  const [planId, setPlanId] = useState<string>('')
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Charge les plans à l'ouverture ; pré-sélectionne celui d'où vient le clic.
  useEffect(() => {
    if (!open) return
    setPlanId(initialPlanId ?? '')
    publicPlansApi.list().then(r => setPlans(r.data)).catch(() => setPlans([]))
  }, [open, initialPlanId])

  if (!open) return null

  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    const isCompany = kind === 'entreprise'
    // Nom retenu : "Prénom Nom" (particulier) ou la raison sociale (société).
    const fullName = isCompany
      ? form.company.trim()
      : `${form.first_name.trim()} ${form.last_name.trim()}`.trim()
    if (!form.email.includes('@')) {
      setError('Un email valide est requis.')
      return
    }
    if (isCompany) {
      if (!form.company.trim() || !form.siret.trim()) {
        setError('Raison sociale et SIRET requis.')
        return
      }
    } else if (!form.first_name.trim() || !form.last_name.trim()) {
      setError('Prénom et nom requis.')
      return
    }
    if (form.phone.trim().length < 6) {
      setError('Un numéro de téléphone est requis.')
      return
    }
    const chosen = plans.find(p => p.id === planId)
    const planLabel = chosen ? `${chosen.name} (${chosen.monthly_price.toFixed(0)} €/mois)` : null
    // Le SIRET (société) est joint au message pour être visible côté Demandes.
    const message = [
      isCompany && form.siret.trim() ? `SIRET : ${form.siret.trim()}` : null,
      form.message.trim() || null,
    ].filter(Boolean).join('\n') || null
    setSending(true); setError(null)
    try {
      await apiClient.post('/public/subscription-requests', {
        full_name: fullName,
        email: form.email.trim(),
        phone: form.phone.trim(),
        company: isCompany ? form.company.trim() : null,
        message,
        plan_id: chosen?.id || null,
        plan_label: planLabel,
      })
      setDone(true)
    } catch (e: any) {
      setError(getErrorMessage(e, "Une erreur est survenue. Réessayez plus tard."))
    } finally {
      setSending(false)
    }
  }

  const inp = 'w-full px-3 py-2.5 text-sm rounded-xl outline-none border border-gray-200 bg-gray-50 focus:bg-white focus:border-brand-navy focus:ring-2 focus:ring-brand-navy/10 transition-all'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Pas de fermeture au clic sur le fond (évite la perte de saisie). */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0"
             style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}>
          <h2 className="text-base font-semibold text-white">Demander une démo</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-white/80">
            <X size={16} />
          </button>
        </div>

        {done ? (
          <div className="px-6 py-10 text-center">
            <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={28} className="text-green-600" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">Demande envoyée</h3>
            <p className="text-sm text-gray-500 mb-5">
              Merci ! Notre équipe vous recontacte rapidement pour la mise en place de votre espace.
            </p>
            <Button onClick={onClose} variant="primary" className="rounded-xl">
              Fermer
            </Button>
          </div>
        ) : (
          <div className="px-6 py-5 space-y-3 overflow-y-auto">
            <p className="text-sm text-gray-500">
              Vous gérez des biens en location ? Laissez-nous vos coordonnées, on s'occupe du reste.
            </p>
            {error && (
              <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
            )}

            {/* Choix de la formule (description + prix) */}
            {plans.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-700">Formule souhaitée</p>
                <div className="space-y-2">
                  {plans.map(p => {
                    const selected = p.id === planId
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setPlanId(selected ? '' : p.id)}
                        className={`w-full text-left rounded-xl border p-3 transition-all ${selected ? 'border-brand-navy bg-brand-navy/5 ring-2 ring-brand-navy/10' : 'border-gray-200 hover:border-gray-300'}`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-gray-900 flex items-center gap-1.5">
                            {selected && <Check size={14} className="text-brand-navy shrink-0" />}
                            {p.name}
                          </span>
                          <span className="text-sm font-bold text-brand-navy whitespace-nowrap">{p.monthly_price.toFixed(0)} €<span className="text-xs font-normal text-gray-500">/mois</span></span>
                        </div>
                        {p.description && <p className="mt-1 text-xs text-gray-500">{p.description}</p>}
                        <p className="mt-1 text-[11px] text-gray-400">
                          {p.property_limit === null ? 'Biens illimités' : `Jusqu'à ${p.property_limit} bien${p.property_limit > 1 ? 's' : ''}`}
                        </p>
                      </button>
                    )
                  })}
                </div>
                <p className="text-[11px] text-gray-400">Optionnel : vous pourrez en discuter avec notre équipe.</p>
              </div>
            )}

            <div className="grid grid-cols-1 gap-3">
              {/* Type de demandeur : particulier ou société */}
              <div className="grid grid-cols-2 gap-2">
                <button type="button" onClick={() => setKind('personne')}
                  className={`px-3 py-2 rounded-xl border text-sm font-medium transition-colors ${kind === 'personne' ? 'border-brand-navy bg-brand-navy/5 text-brand-navy' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                  Particulier
                </button>
                <button type="button" onClick={() => setKind('entreprise')}
                  className={`px-3 py-2 rounded-xl border text-sm font-medium transition-colors ${kind === 'entreprise' ? 'border-brand-navy bg-brand-navy/5 text-brand-navy' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                  Société
                </button>
              </div>
              {kind === 'personne' ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input className={inp} placeholder="Prénom *" value={form.first_name}
                    onChange={e => set('first_name', e.target.value)} />
                  <input className={inp} placeholder="Nom *" value={form.last_name}
                    onChange={e => set('last_name', e.target.value)} />
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input className={inp} placeholder="Raison sociale *" value={form.company}
                    onChange={e => set('company', e.target.value)} />
                  <SiretInput className={inp} placeholder="SIRET *" value={form.siret}
                    onChange={v => set('siret', v)}
                    onResolved={name => { if (!form.company.trim()) set('company', name) }} />
                </div>
              )}
              <input className={inp} placeholder={kind === 'personne' ? 'Email *' : 'Email professionnel *'} type="email" value={form.email}
                onChange={e => set('email', e.target.value)} />
              <input className={inp} placeholder="Téléphone *" value={form.phone}
                onChange={e => set('phone', e.target.value)} />
              <textarea className={`${inp} resize-none`} rows={3} placeholder="Votre besoin (optionnel)"
                value={form.message} onChange={e => set('message', e.target.value)} />
            </div>
            <button onClick={submit} disabled={sending}
              className="w-full py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-60"
              style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}>
              <Send size={15} /> {sending ? 'Envoi…' : 'Envoyer ma demande'}
            </button>
            <p className="text-[11px] text-gray-400 text-center">
              Vos données ne servent qu'à vous recontacter. Aucun engagement.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
