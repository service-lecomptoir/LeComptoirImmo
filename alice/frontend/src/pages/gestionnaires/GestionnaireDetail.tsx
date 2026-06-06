import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ShieldOff, ShieldCheck, Building2, Save, X, AlertTriangle, CalendarClock, RotateCcw } from 'lucide-react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import clsx from 'clsx'
import { gestionnairesApi } from '@/api/gestionnaires'
import { plansApi } from '@/api/plans'
import PhoneInput from '@/components/PhoneInput'
import { ROLE_OPTIONS } from './GestionnaireList'
import type { Gestionnaire, Plan, GestionnaireProperty } from '@/types'

interface ConfirmModalProps {
  action: 'block' | 'unblock'
  name: string
  onConfirm: () => void
  onCancel: () => void
}

function ConfirmModal({ action, name, onConfirm, onCancel }: ConfirmModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center gap-4 mb-5">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${action === 'block' ? 'bg-red-100' : 'bg-emerald-100'}`}>
            <AlertTriangle size={22} className={action === 'block' ? 'text-red-600' : 'text-emerald-600'} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">
              {action === 'block' ? 'Bloquer ce gestionnaire ?' : 'Débloquer ce gestionnaire ?'}
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">{name}</p>
          </div>
        </div>

        <p className="text-sm text-gray-600 mb-6">
          {action === 'block'
            ? 'Le gestionnaire et tous ses propriétaires et locataires seront désactivés. Vous pourrez les réactiver en débloquant le gestionnaire.'
            : 'Le gestionnaire et tous les utilisateurs bloqués en cascade seront réactivés.'}
        </p>

        <div className="flex justify-end gap-3">
          <button onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            Annuler
          </button>
          <button
            onClick={onConfirm}
            className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors ${action === 'block' ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'}`}
          >
            {action === 'block' ? 'Bloquer' : 'Débloquer'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function GestionnaireDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [gestionnaire, setGestionnaire] = useState<Gestionnaire | null>(null)
  const [properties, setProperties] = useState<GestionnaireProperty[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [confirmAction, setConfirmAction] = useState<'block' | 'unblock' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Form state
  const [editFullName, setEditFullName] = useState('')
  const [editOwnerFirst, setEditOwnerFirst] = useState('')
  const [editOwnerLast, setEditOwnerLast] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editRole, setEditRole] = useState<'gestionnaire' | 'gestionnaire_proprio'>('gestionnaire')
  const [editPhone, setEditPhone] = useState<string | null>(null)
  const [editPlanId, setEditPlanId] = useState<string>('')
  const [editLimitOverride, setEditLimitOverride] = useState<string>('')
  const [editPriceOverride, setEditPriceOverride] = useState<string>('')
  const [editNotes, setEditNotes] = useState('')

  useEffect(() => {
    if (!id) return
    Promise.all([
      gestionnairesApi.get(id),
      gestionnairesApi.getProperties(id),
      plansApi.list(),
    ]).then(([gRes, pRes, plRes]) => {
      const g = gRes.data
      setGestionnaire(g)
      setProperties(pRes.data)
      setPlans(plRes.data)
      // Init form
      setEditFullName(g.full_name)
      {
        const _p = (g.owner_full_name ?? '').trim().split(/\s+/).filter(Boolean)
        setEditOwnerFirst(_p.shift() ?? '')
        setEditOwnerLast(_p.join(' '))
      }
      setEditEmail(g.email)
      setEditRole(g.role === 'gestionnaire_proprio' ? 'gestionnaire_proprio' : 'gestionnaire')
      setEditPhone(g.license?.phone ?? null)
      setEditPlanId(g.license?.plan_id || '')
      setEditLimitOverride(g.license?.property_limit_override?.toString() || '')
      setEditPriceOverride(g.license?.monthly_price_override?.toString() || '')
      setEditNotes(g.license?.notes || '')
    }).finally(() => setLoading(false))
  }, [id])

  const handleSave = async () => {
    if (!id) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await gestionnairesApi.update(id, {
        full_name: editFullName,
        owner_full_name: `${editOwnerFirst.trim()} ${editOwnerLast.trim()}`.trim() || null,
        email: editEmail,
        role: editRole,
        phone: editPhone,
        plan_id: editPlanId || null,
        property_limit_override: editLimitOverride ? parseInt(editLimitOverride) : null,
        monthly_price_override: editPriceOverride ? parseFloat(editPriceOverride) : null,
        notes: editNotes || null,
      })
      setGestionnaire(data)
      setSuccess('Modifications enregistrées')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      setError(axiosError?.response?.data?.detail || 'Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const handleBlockAction = async () => {
    if (!id || !confirmAction) return
    setActionLoading(true)
    setConfirmAction(null)
    setError(null)
    try {
      const fn = confirmAction === 'block' ? gestionnairesApi.block : gestionnairesApi.unblock
      const { data } = await fn(id)
      setGestionnaire(data)
      setSuccess(confirmAction === 'block' ? 'Gestionnaire bloqué' : 'Gestionnaire débloqué')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      setError(axiosError?.response?.data?.detail || 'Erreur lors de l\'action')
    } finally {
      setActionLoading(false)
    }
  }

  const handleReactivate = async () => {
    if (!id) return
    setActionLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await gestionnairesApi.reactivate(id)
      setGestionnaire(data)
      setSuccess('Désactivation annulée — le compte reste actif')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      setError(axiosError?.response?.data?.detail || 'Erreur lors de la réactivation')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }

  if (!gestionnaire) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
          Gestionnaire introuvable
        </div>
      </div>
    )
  }

  const isBlocked = gestionnaire.license?.is_blocked ?? false
  const scheduledUntil = gestionnaire.license?.access_until ?? null

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 sm:gap-4 mb-8">
        <button
          onClick={() => navigate('/gestionnaires')}
          className="p-2 rounded-xl hover:bg-gray-100 transition-colors text-gray-500"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{gestionnaire.full_name}</h1>
          <p className="text-gray-500 text-sm mt-0.5">{gestionnaire.email}</p>
        </div>

        {/* Bouton Bloquer / Débloquer */}
        <button
          onClick={() => setConfirmAction(isBlocked ? 'unblock' : 'block')}
          disabled={actionLoading}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl transition-colors disabled:opacity-60 ${isBlocked
            ? 'bg-emerald-600 text-white hover:bg-emerald-700'
            : 'bg-red-600 text-white hover:bg-red-700'
          }`}
        >
          {isBlocked ? <ShieldCheck size={16} /> : <ShieldOff size={16} />}
          {actionLoading ? 'En cours…' : isBlocked ? 'Débloquer' : 'Bloquer'}
        </button>
      </div>

      {/* Alertes */}
      {error && (
        <div className="mb-5 flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <X size={14} />
          {error}
        </div>
      )}
      {success && (
        <div className="mb-5 flex items-center gap-2 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700">
          {success}
        </div>
      )}

      {isBlocked && (
        <div className="mb-6 flex items-center gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
          <AlertTriangle size={16} className="text-red-600 flex-shrink-0" />
          <p className="text-sm text-red-700 font-medium">
            Ce gestionnaire est bloqué. Ses propriétaires et locataires sont désactivés en cascade.
          </p>
        </div>
      )}

      {!isBlocked && scheduledUntil && (
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center gap-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl">
          <CalendarClock size={16} className="text-amber-600 flex-shrink-0" />
          <p className="text-sm text-amber-800 font-medium flex-1">
            Désactivation programmée — le compte sera bloqué le{' '}
            {format(new Date(scheduledUntil), 'dd/MM/yyyy', { locale: fr })}.
          </p>
          <button
            onClick={handleReactivate}
            disabled={actionLoading}
            className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 transition-colors"
          >
            <RotateCcw size={15} />
            {actionLoading ? 'En cours…' : 'Réactiver'}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Colonne principale — Edition */}
        <div className="lg:col-span-2 space-y-6">
          {/* Informations compte */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-5">Informations du compte</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Type de compte</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {ROLE_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setEditRole(opt.value)}
                      className={clsx(
                        'text-left px-3 py-2.5 rounded-lg border text-xs transition-colors',
                        editRole === opt.value
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-900'
                          : 'border-gray-200 hover:border-gray-300 text-gray-700'
                      )}
                    >
                      <div className="font-semibold">{opt.label}</div>
                      <div className={clsx('mt-0.5', editRole === opt.value ? 'text-indigo-500' : 'text-gray-400')}>{opt.description}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Nom de compte</label>
                <input
                  type="text"
                  value={editFullName}
                  onChange={e => setEditFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Nom et prénom du propriétaire</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={editOwnerFirst}
                    onChange={e => setEditOwnerFirst(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Prénom"
                  />
                  <input
                    type="text"
                    value={editOwnerLast}
                    onChange={e => setEditOwnerLast(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Nom"
                  />
                </div>
                <p className="mt-1 text-[11px] text-gray-400">Bailleur sur le bail, l'attestation de loyer et le formulaire tiers payant.</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                <input
                  type="email"
                  value={editEmail}
                  onChange={e => setEditEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Téléphone</label>
                <PhoneInput value={editPhone} onChange={setEditPhone} />
              </div>
            </div>
          </div>

          {/* Licence */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-5">Licence & tarification</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Plan tarifaire</label>
                <select
                  value={editPlanId}
                  onChange={e => setEditPlanId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">-- Aucun plan --</option>
                  {plans.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {p.monthly_price}€/mois
                      {p.property_limit ? ` (${p.property_limit} bien${p.property_limit > 1 ? 's' : ''} max)` : ' (illimité)'}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Limite biens (override)
                  </label>
                  <input
                    type="number"
                    value={editLimitOverride}
                    onChange={e => setEditLimitOverride(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Utilise limite du plan"
                    min={1}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Prix/mois override (€)
                  </label>
                  <input
                    type="number"
                    value={editPriceOverride}
                    onChange={e => setEditPriceOverride(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Prix du plan"
                    min={0}
                    step={0.01}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Notes internes</label>
                <textarea
                  value={editNotes}
                  onChange={e => setEditNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  rows={3}
                  placeholder="Notes optionnelles..."
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition-colors"
              >
                <Save size={15} />
                {saving ? 'Enregistrement...' : 'Enregistrer'}
              </button>
            </div>
          </div>

          {/* Biens */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-semibold text-gray-800">Biens gérés</h2>
              <span className="text-sm text-gray-500">{properties.length} bien{properties.length > 1 ? 's' : ''}</span>
            </div>
            {properties.length === 0 ? (
              <p className="text-sm text-gray-400">Aucun bien créé par ce gestionnaire</p>
            ) : (
              <div className="space-y-2">
                {properties.map(p => (
                  <div key={p.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50">
                    <Building2 size={16} className="text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                      {(p.address || p.city) && (
                        <p className="text-xs text-gray-500 truncate">
                          {[p.address, p.zip_code, p.city].filter(Boolean).join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar droite — Infos */}
        <div className="space-y-5">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Résumé</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Statut</span>
                <span className={`font-medium ${isBlocked ? 'text-red-600' : gestionnaire.is_active ? 'text-emerald-600' : 'text-gray-500'}`}>
                  {isBlocked ? 'Bloque' : gestionnaire.is_active ? 'Actif' : 'Inactif'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Plan</span>
                <span className="font-medium text-gray-800">
                  {gestionnaire.plan?.name || '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Limite biens</span>
                <span className="font-medium text-gray-800">
                  {gestionnaire.effective_property_limit !== null
                    ? gestionnaire.effective_property_limit
                    : 'Illimité'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Biens créés</span>
                <span className="font-medium text-gray-800">{gestionnaire.property_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Créé le</span>
                <span className="font-medium text-gray-800">
                  {format(new Date(gestionnaire.created_at), 'dd/MM/yyyy', { locale: fr })}
                </span>
              </div>
              {gestionnaire.license && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Licence depuis</span>
                  <span className="font-medium text-gray-800">
                    {format(new Date(gestionnaire.license.created_at), 'dd/MM/yyyy', { locale: fr })}
                  </span>
                </div>
              )}
              {!isBlocked && scheduledUntil && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Désactivation le</span>
                  <span className="font-medium text-amber-700">
                    {format(new Date(scheduledUntil), 'dd/MM/yyyy', { locale: fr })}
                  </span>
                </div>
              )}
            </div>
          </div>

          {gestionnaire.license?.notes && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
              <p className="text-xs font-semibold text-amber-700 mb-1.5">Notes internes</p>
              <p className="text-sm text-amber-800">{gestionnaire.license.notes}</p>
            </div>
          )}

          {gestionnaire.license?.stripe_subscription_id && (() => {
            const st = gestionnaire.license.stripe_status || ''
            const active = st === 'active' || st === 'trialing'
            const label = st === 'active' ? 'Actif' : st === 'trialing' ? 'Essai'
              : st === 'past_due' ? 'Paiement en retard' : st === 'unpaid' ? 'Impayé'
              : st === 'canceled' ? 'Annulé' : (st || '—')
            const pm = gestionnaire.license.stripe_payment_method_type
            return (
              <div className="bg-white border border-gray-200 rounded-2xl p-4">
                <p className="text-xs font-semibold text-gray-500 mb-3">Abonnement Stripe</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500">Statut</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      active ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                      {label}
                    </span>
                  </div>
                  {pm && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Moyen de paiement</span>
                      <span className="font-medium text-gray-800">
                        {pm === 'sepa_debit' ? 'Prélèvement SEPA' : 'Carte bancaire'}
                      </span>
                    </div>
                  )}
                  {gestionnaire.license.stripe_current_period_end && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Prochaine échéance</span>
                      <span className="font-medium text-gray-800">
                        {format(new Date(gestionnaire.license.stripe_current_period_end), 'dd/MM/yyyy', { locale: fr })}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })()}
        </div>
      </div>

      {/* Modal de confirmation */}
      {confirmAction && (
        <ConfirmModal
          action={confirmAction}
          name={gestionnaire.full_name}
          onConfirm={handleBlockAction}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  )
}
