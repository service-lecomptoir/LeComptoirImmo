import { useEffect, useState } from 'react'
import { Hotel, Plus, KeyRound, Loader2 } from 'lucide-react'
import { sejourApi, type SejourManager, type SejourStats } from '@/api/sejour'

function errMsg(e: unknown): string {
  const x = e as { response?: { data?: { detail?: unknown } } }
  const d = x?.response?.data?.detail
  return typeof d === 'string' ? d : 'Une erreur est survenue.'
}

export default function SejourList() {
  const [managers, setManagers] = useState<SejourManager[]>([])
  const [stats, setStats] = useState<SejourStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', full_name: '', phone: '', password: '' })
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    setError('')
    Promise.all([sejourApi.list(), sejourApi.stats()])
      .then(([m, s]) => { setManagers(m.data); setStats(s.data) })
      .catch((e) => setError(errMsg(e)))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await sejourApi.create({
        email: form.email, full_name: form.full_name,
        phone: form.phone || undefined, password: form.password,
      })
      setShowForm(false)
      setForm({ email: '', full_name: '', phone: '', password: '' })
      load()
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const toggle = async (m: SejourManager) => {
    try { await sejourApi.update(m.id, { is_active: !m.is_active }); load() }
    catch (e) { setError(errMsg(e)) }
  }

  const resetPwd = async (m: SejourManager) => {
    const np = window.prompt(`Nouveau mot de passe pour ${m.email} (min. 8 caractères) :`)
    if (!np) return
    try { await sejourApi.resetPassword(m.id, np); alert('Mot de passe réinitialisé.') }
    catch (e) { setError(errMsg(e)) }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Hotel className="text-indigo-600" /> Le Comptoir Séjour
          </h1>
          <p className="text-gray-500 text-sm">Gestion locative courte durée — comptes gestionnaires</p>
        </div>
        <button onClick={() => setShowForm((s) => !s)}
          className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-4 py-2 text-sm font-medium">
          <Plus size={16} /> Nouveau gestionnaire
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {[
          ['Gestionnaires', stats?.managers],
          ['Actifs', stats?.active_managers],
          ['Logements', stats?.units],
          ['Réservations', stats?.reservations],
        ].map(([label, val]) => (
          <div key={label as string} className="bg-white border rounded-xl p-4">
            <div className="text-2xl font-bold text-gray-900">{val ?? '—'}</div>
            <div className="text-xs text-gray-500">{label}</div>
          </div>
        ))}
      </div>

      {error && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}

      {showForm && (
        <form onSubmit={create} className="bg-white border rounded-xl p-4 mb-6 grid sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1">E-mail *</label>
            <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Nom du compte</label>
            <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Téléphone</label>
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Mot de passe * (min. 8)</label>
            <input type="text" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full border rounded-lg px-3 py-2" placeholder="Communiqué au gestionnaire" />
          </div>
          <div className="sm:col-span-2">
            <button disabled={saving} className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-4 py-2 text-sm disabled:opacity-60">
              {saving ? 'Création…' : 'Créer le gestionnaire'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left">
            <tr>
              <th className="px-4 py-2">Nom du compte</th>
              <th className="px-4 py-2">E-mail</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                <Loader2 className="animate-spin inline" size={18} /> Chargement…
              </td></tr>
            )}
            {!loading && managers.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Aucun gestionnaire Séjour.</td></tr>
            )}
            {managers.map((m) => (
              <tr key={m.id} className="border-t">
                <td className="px-4 py-2">{m.full_name || '—'}</td>
                <td className="px-4 py-2">{m.email}</td>
                <td className="px-4 py-2">
                  <button onClick={() => toggle(m)}
                    className={`text-xs px-2 py-0.5 rounded ${m.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-600'}`}>
                    {m.is_active ? 'Actif' : 'Inactif'}
                  </button>
                </td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => resetPwd(m)} title="Réinitialiser le mot de passe"
                    className="text-indigo-600 hover:text-indigo-700"><KeyRound size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
