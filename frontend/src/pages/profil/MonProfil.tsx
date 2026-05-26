import { useState } from 'react'
import { Save } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'

export default function MonProfil() {
  const { user, fetchMe } = useAuthStore()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [address, setAddress] = useState(user?.address ?? '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const save = async () => {
    setSaving(true); setMsg(null); setErr(null)
    try {
      await authApi.updateProfile({ full_name: fullName, phone: phone || null, address: address || null })
      await fetchMe()
      setMsg('Profil mis à jour.')
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Erreur lors de l'enregistrement")
    } finally {
      setSaving(false)
    }
  }

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const lbl = 'block text-xs font-medium text-gray-600 mb-1'

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mon profil</h1>
        <p className="text-gray-500 text-sm mt-1">
          Vos coordonnées d'agence — affichées dans la barre latérale.
        </p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        {msg && <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">{msg}</div>}
        {err && <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{err}</div>}
        <div>
          <label className={lbl}>Email</label>
          <input className={`${inp} bg-gray-50 text-gray-500`} value={user?.email ?? ''} disabled />
        </div>
        <div>
          <label className={lbl}>Nom complet</label>
          <input className={inp} value={fullName} onChange={e => setFullName(e.target.value)} />
        </div>
        <div>
          <label className={lbl}>Téléphone</label>
          <input className={inp} value={phone} onChange={e => setPhone(e.target.value)} placeholder="06 12 34 56 78" />
        </div>
        <div>
          <label className={lbl}>Adresse</label>
          <textarea className={`${inp} resize-none`} rows={2} value={address}
            onChange={e => setAddress(e.target.value)} placeholder="12 rue de la République, 75001 Paris" />
        </div>
        <div className="flex justify-end">
          <button onClick={save} disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
            <Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      </div>
    </div>
  )
}
