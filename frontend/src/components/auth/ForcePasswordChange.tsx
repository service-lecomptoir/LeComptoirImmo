import { useState } from 'react'
import { BRAND } from '@/lib/brand'
import { Button } from '@/components/ui'
import { Eye, EyeOff, Lock, ShieldCheck, LogOut } from 'lucide-react'
import { apiClient } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import { LogoMark } from '@/components/common/Logo'
import { toast } from '@/store/toast'

/**
 * Écran bloquant affiché tant que le compte est en « mot de passe temporaire »
 * (gestionnaire provisionné depuis Alice, ou compte réinitialisé par un admin).
 * L'utilisateur ne peut pas accéder à l'application avant d'avoir défini son
 * propre mot de passe. Disponible pour tous les rôles.
 */
export function ForcePasswordChange() {
  const { fetchMe, logout, user } = useAuthStore()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNext, setShowNext] = useState(false)
  const [saving, setSaving] = useState(false)

  const tooShort = next.length > 0 && next.length < 8
  const mismatch = confirm.length > 0 && next !== confirm
  const sameAsTemp = next.length > 0 && next === current
  const canSubmit =
    current.length > 0 && next.length >= 8 && next === confirm && !sameAsTemp && !saving

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setSaving(true)
    try {
      await apiClient.patch('/users/me/password', {
        current_password: current,
        new_password: next,
      })
      // Recharge le profil : must_change_password repasse à false côté serveur,
      // ce qui débloque l'accès à l'application.
      await fetchMe()
      toast.success('Mot de passe mis à jour. Bienvenue !')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Mot de passe temporaire incorrect.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10"
      style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1E3A5F 100%)' }}>
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-7 sm:p-9">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: BRAND.navy }}>
            <LogoMark size={26} className="text-white" />
          </div>
          <div className="min-w-0">
            <p className="font-bold text-gray-900 leading-tight">Le Comptoir Immo</p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>
        </div>

        <div className="flex items-start gap-3 mb-5 p-3 rounded-xl bg-amber-50 border border-amber-200">
          <ShieldCheck size={20} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-900">Mot de passe temporaire</p>
            <p className="text-xs text-amber-800 mt-0.5">
              Pour votre sécurité, définissez un nouveau mot de passe personnel avant
              d'accéder à votre espace.
            </p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <Field label="Mot de passe temporaire" icon>
            <input
              type={showCurrent ? 'text' : 'password'}
              value={current} onChange={e => setCurrent(e.target.value)}
              autoFocus autoComplete="current-password"
              className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Celui reçu de votre gestionnaire" />
            <ToggleEye show={showCurrent} onClick={() => setShowCurrent(v => !v)} />
          </Field>

          <Field label="Nouveau mot de passe" icon>
            <input
              type={showNext ? 'text' : 'password'}
              value={next} onChange={e => setNext(e.target.value)}
              autoComplete="new-password"
              className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="8 caractères minimum" />
            <ToggleEye show={showNext} onClick={() => setShowNext(v => !v)} />
          </Field>
          {tooShort && <p className="text-xs text-red-600 -mt-2">8 caractères minimum.</p>}
          {sameAsTemp && <p className="text-xs text-red-600 -mt-2">Choisissez un mot de passe différent du temporaire.</p>}

          <Field label="Confirmer le nouveau mot de passe" icon>
            <input
              type={showNext ? 'text' : 'password'}
              value={confirm} onChange={e => setConfirm(e.target.value)}
              autoComplete="new-password"
              className="w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Saisir à nouveau" />
          </Field>
          {mismatch && <p className="text-xs text-red-600 -mt-2">Les deux mots de passe ne correspondent pas.</p>}

          <Button type="submit" variant="primary" fullWidth disabled={!canSubmit}
            isLoading={saving} className="py-2.5 font-semibold">
            {saving ? 'Enregistrement…' : 'Définir mon mot de passe'}
          </Button>
        </form>

        <button onClick={logout}
          className="mt-4 w-full inline-flex items-center justify-center gap-1.5 text-xs text-gray-500 hover:text-gray-700">
          <LogOut size={13} /> Se déconnecter
        </button>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; icon?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      <div className="relative">
        <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        {children}
      </div>
    </div>
  )
}

function ToggleEye({ show, onClick }: { show: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
      {show ? <EyeOff size={16} /> : <Eye size={16} />}
    </button>
  )
}

export default ForcePasswordChange
