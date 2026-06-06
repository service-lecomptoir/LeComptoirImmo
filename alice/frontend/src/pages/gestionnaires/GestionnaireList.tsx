import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Search, Building2 } from 'lucide-react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import clsx from 'clsx'
import { gestionnairesApi, type GestionnaireCreateData } from '@/api/gestionnaires'
import { plansApi } from '@/api/plans'
import PhoneInput from '@/components/PhoneInput'
import type { Gestionnaire, Plan } from '@/types'

function StatusBadge({ isActive, isBlocked }: { isActive: boolean; isBlocked: boolean }) {
  if (isBlocked) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700">
        <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
        Bloque
      </span>
    )
  }
  if (!isActive) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
        Inactif
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      Actif
    </span>
  )
}

interface CreateModalProps {
  plans: Plan[]
  onClose: () => void
  onCreated: (g: Gestionnaire) => void
  initial?: { full_name?: string; email?: string }
}

export const ROLE_OPTIONS: { value: 'gestionnaire' | 'gestionnaire_proprio'; label: string; description: string }[] = [
  { value: 'gestionnaire', label: 'Gestionnaire mandataire', description: 'Gère des biens pour le compte de propriétaires tiers' },
  { value: 'gestionnaire_proprio', label: 'Gestionnaire-Propriétaire', description: 'Gère et possède ses propres biens (même personne)' },
]

function CreateModal({ plans, onClose, onCreated, initial }: CreateModalProps) {
  const [form, setForm] = useState<GestionnaireCreateData>({
    email: initial?.email ?? '',
    full_name: initial?.full_name ?? '',
    owner_full_name: null,
    password: '',
    role: 'gestionnaire',
    plan_id: null,
    property_limit_override: null,
    monthly_price_override: null,
    notes: null,
    phone: null,
    address: null,
  })
  const [ownerFirst, setOwnerFirst] = useState('')
  const [ownerLast, setOwnerLast] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Règle : le plan Free est réservé aux comptes Gestionnaire-Propriétaire.
  const selectedPlanIsFree = plans.some(
    p => p.id === form.plan_id && (p.name || '').trim().toLowerCase() === 'free',
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const owner_full_name = `${ownerFirst.trim()} ${ownerLast.trim()}`.trim() || null
      const { data } = await gestionnairesApi.create({ ...form, owner_full_name })
      onCreated(data)
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      setError(axiosError?.response?.data?.detail || 'Erreur lors de la création')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col overflow-hidden">
        <div className="shrink-0 flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-base font-semibold text-gray-800">Nouveau gestionnaire</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors text-gray-500">
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col min-h-0 flex-1">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {error && (
            <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Type de compte *</label>
              <div className="grid grid-cols-2 gap-2">
                {ROLE_OPTIONS.map(opt => {
                  const disabled = selectedPlanIsFree && opt.value !== 'gestionnaire_proprio'
                  return (
                  <button
                    key={opt.value}
                    type="button"
                    disabled={disabled}
                    onClick={() => setForm(f => ({ ...f, role: opt.value }))}
                    className={clsx(
                      'text-left px-3 py-2.5 rounded-lg border text-xs transition-colors',
                      disabled && 'opacity-40 cursor-not-allowed',
                      form.role === opt.value
                        ? 'border-indigo-500 bg-indigo-50 text-indigo-900'
                        : 'border-gray-200 hover:border-gray-300 text-gray-700'
                    )}
                  >
                    <div className="font-semibold">{opt.label}</div>
                    <div className={clsx('mt-0.5', form.role === opt.value ? 'text-indigo-500' : 'text-gray-400')}>{opt.description}</div>
                  </button>
                  )
                })}
              </div>
              {selectedPlanIsFree && (
                <p className="mt-1.5 text-[11px] text-amber-600">Le plan Free est réservé aux comptes Gestionnaire-Propriétaire.</p>
              )}
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Nom de compte *</label>
              <input
                type="text"
                value={form.full_name}
                onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Ex : Résidence Tatie"
                required
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Nom et prénom du propriétaire</label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  value={ownerFirst}
                  onChange={e => setOwnerFirst(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Prénom"
                />
                <input
                  type="text"
                  value={ownerLast}
                  onChange={e => setOwnerLast(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Nom"
                />
              </div>
              <p className="mt-1 text-[11px] text-gray-400">Bailleur sur le bail, l'attestation de loyer et le formulaire tiers payant.</p>
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Email *</label>
              <input
                type="email"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="gestionnaire@cabinet.fr"
                required
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Mot de passe *</label>
              <input
                type="password"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Minimum 8 caractères"
                required
                minLength={8}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Téléphone</label>
              <PhoneInput
                value={form.phone}
                onChange={v => setForm(f => ({ ...f, phone: v }))}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Adresse</label>
              <textarea
                value={form.address || ''}
                onChange={e => setForm(f => ({ ...f, address: e.target.value || null }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                rows={2}
                placeholder="12 rue de la République, 75001 Paris"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Plan tarifaire</label>
              <select
                value={form.plan_id || ''}
                onChange={e => {
                  const id = e.target.value || null
                  const isFree = plans.some(p => p.id === id && (p.name || '').trim().toLowerCase() === 'free')
                  setForm(f => ({ ...f, plan_id: id, role: isFree ? 'gestionnaire_proprio' : f.role }))
                }}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">-- Aucun plan --</option>
                {plans.map(p => (
                  <option key={p.id} value={p.id}>{p.name} — {p.monthly_price}€/mois</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Limite biens (override)</label>
              <input
                type="number"
                value={form.property_limit_override ?? ''}
                onChange={e => setForm(f => ({ ...f, property_limit_override: e.target.value ? parseInt(e.target.value) : null }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Illimité si vide"
                min={1}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Prix/mois override (€)</label>
              <input
                type="number"
                value={form.monthly_price_override ?? ''}
                onChange={e => setForm(f => ({ ...f, monthly_price_override: e.target.value ? parseFloat(e.target.value) : null }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Prix du plan si vide"
                min={0}
                step={0.01}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Notes internes</label>
              <textarea
                value={form.notes || ''}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value || null }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                rows={2}
                placeholder="Notes optionnelles..."
              />
            </div>
          </div>
          </div>

          <div className="shrink-0 flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              Annuler
            </button>
            <button type="submit" disabled={saving}
              className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 transition-colors">
              {saving ? 'Création…' : 'Créer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function GestionnaireList() {
  const navigate = useNavigate()
  const location = useLocation()
  const prefill = (location.state as { prefill?: { full_name?: string; email?: string } } | null)?.prefill
  const [gestionnaires, setGestionnaires] = useState<Gestionnaire[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(!!prefill)

  useEffect(() => {
    Promise.all([gestionnairesApi.list(), plansApi.list()])
      .then(([gRes, pRes]) => {
        setGestionnaires(gRes.data)
        setPlans(pRes.data)
      })
      .finally(() => setLoading(false))
  }, [])

  const filtered = gestionnaires.filter(g =>
    g.full_name.toLowerCase().includes(search.toLowerCase()) ||
    g.email.toLowerCase().includes(search.toLowerCase())
  )

  const handleCreated = (g: Gestionnaire) => {
    setGestionnaires(prev => [g, ...prev])
    setShowCreate(false)
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestionnaires</h1>
          <p className="text-gray-500 text-sm mt-1">{gestionnaires.length} compte{gestionnaires.length > 1 ? 's' : ''} au total</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200"
        >
          <Plus size={16} />
          Nouveau gestionnaire
        </button>
      </div>

      {/* Recherche */}
      <div className="relative mb-6 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher par nom ou email..."
          className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Nom</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Email</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Plan</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Biens</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Créé le</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-sm text-gray-400">
                    {search ? 'Aucun gestionnaire ne correspond à votre recherche' : 'Aucun gestionnaire'}
                  </td>
                </tr>
              ) : (
                filtered.map(g => (
                  <tr
                    key={g.id}
                    onClick={() => navigate(`/gestionnaires/${g.id}`)}
                    className="hover:bg-indigo-50/50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                          <span className="text-indigo-700 text-xs font-semibold">
                            {g.full_name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <span className="font-medium text-gray-900 text-sm">{g.full_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{g.email}</td>
                    <td className="px-6 py-4">
                      {g.role === 'gestionnaire_proprio' ? (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-violet-50 text-violet-700">
                          Gest.-Proprio
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-blue-50 text-blue-600">
                          Mandataire
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {g.plan ? (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-indigo-50 text-indigo-700">
                          {g.plan.name}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-sm text-gray-600">
                        <Building2 size={13} className="text-gray-400 flex-shrink-0" />
                        <span className="whitespace-nowrap">
                          {g.property_count}
                          {g.effective_property_limit !== null
                            ? ` / ${g.effective_property_limit}`
                            : ''}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge isActive={g.is_active} isBlocked={g.license?.is_blocked ?? false} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {format(new Date(g.created_at), 'dd/MM/yyyy', { locale: fr })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateModal
          plans={plans}
          initial={prefill}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  )
}
