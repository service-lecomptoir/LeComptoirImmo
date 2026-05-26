import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Infinity } from 'lucide-react'
import { plansApi, type PlanCreateData, type PlanUpdateData } from '@/api/plans'
import type { Plan } from '@/types'

interface PlanModalProps {
  plan?: Plan | null
  onClose: () => void
  onSaved: (p: Plan) => void
}

function PlanModal({ plan, onClose, onSaved }: PlanModalProps) {
  const isEdit = !!plan
  const [form, setForm] = useState<PlanCreateData>({
    name: plan?.name || '',
    description: plan?.description || '',
    property_limit: plan?.property_limit ?? null,
    monthly_price: plan?.monthly_price ?? 0,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      let data: Plan
      if (isEdit && plan) {
        const updateData: PlanUpdateData = {
          name: form.name,
          description: form.description,
          property_limit: form.property_limit,
          monthly_price: form.monthly_price,
        }
        const res = await plansApi.update(plan.id, updateData)
        data = res.data
      } else {
        const res = await plansApi.create(form)
        data = res.data
      }
      onSaved(data)
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      setError(axiosError?.response?.data?.detail || 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-base font-semibold text-gray-800">
            {isEdit ? 'Modifier le plan' : 'Nouveau plan'}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors text-gray-500">
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {error && (
            <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Nom du plan *</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Ex: Starter, Pro, Enterprise"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea
              value={form.description || ''}
              onChange={e => setForm(f => ({ ...f, description: e.target.value || null }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              rows={2}
              placeholder="Description optionnelle..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Limite de biens</label>
              <input
                type="number"
                value={form.property_limit ?? ''}
                onChange={e => setForm(f => ({ ...f, property_limit: e.target.value ? parseInt(e.target.value) : null }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Vide = illimite"
                min={1}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Prix mensuel (€) *</label>
              <input
                type="number"
                value={form.monthly_price}
                onChange={e => setForm(f => ({ ...f, monthly_price: parseFloat(e.target.value) || 0 }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                min={0}
                step={0.01}
                required
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              Annuler
            </button>
            <button type="submit" disabled={saving}
              className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 transition-colors">
              {saving ? 'Enregistrement...' : isEdit ? 'Modifier' : 'Creer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function PlanList() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState<{ open: boolean; plan?: Plan | null }>({ open: false })
  const [deactivating, setDeactivating] = useState<string | null>(null)

  useEffect(() => {
    plansApi.list()
      .then(res => setPlans(res.data))
      .finally(() => setLoading(false))
  }, [])

  const handleSaved = (p: Plan) => {
    setPlans(prev => {
      const idx = prev.findIndex(x => x.id === p.id)
      if (idx >= 0) {
        const next = [...prev]
        next[idx] = p
        return next
      }
      return [p, ...prev]
    })
    setModal({ open: false })
  }

  const handleDeactivate = async (plan: Plan) => {
    if (!confirm(`Desactiver le plan "${plan.name}" ?`)) return
    setDeactivating(plan.id)
    try {
      await plansApi.deactivate(plan.id)
      setPlans(prev => prev.filter(p => p.id !== plan.id))
    } catch {
      // silently
    } finally {
      setDeactivating(null)
    }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Plans tarifaires</h1>
          <p className="text-gray-500 text-sm mt-1">{plans.length} plan(s) actif(s)</p>
        </div>
        <button
          onClick={() => setModal({ open: true, plan: null })}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200"
        >
          <Plus size={16} />
          Nouveau plan
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Plan</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Limite biens</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Prix/mois</th>
                <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Gestionnaires</th>
                <th className="px-6 py-3.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {plans.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-sm text-gray-400">
                    Aucun plan tarifaire
                  </td>
                </tr>
              ) : (
                plans.map(plan => (
                  <tr key={plan.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">{plan.name}</p>
                        {plan.description && (
                          <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]">{plan.description}</p>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {plan.property_limit !== null ? (
                        <span className="text-sm font-medium text-gray-700">{plan.property_limit} biens</span>
                      ) : (
                        <div className="flex items-center gap-1 text-indigo-600">
                          <Infinity size={14} />
                          <span className="text-sm font-medium">Illimite</span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-semibold text-gray-900">
                        {plan.monthly_price.toFixed(2)} €
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-indigo-50 text-indigo-700">
                        {plan.gestionnaire_count} abonne{plan.gestionnaire_count > 1 ? 's' : ''}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setModal({ open: true, plan })}
                          className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="Modifier"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => handleDeactivate(plan)}
                          disabled={deactivating === plan.id}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-40"
                          title="Desactiver"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {modal.open && (
        <PlanModal
          plan={modal.plan}
          onClose={() => setModal({ open: false })}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
