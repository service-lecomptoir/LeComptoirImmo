import { useState } from 'react'
import { Check } from 'lucide-react'
import { apiClient } from '@/api/client'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'
import type { User } from '@/types/auth'

type Theme = 'marine_center' | 'marine_band' | 'epure'

const NAVY = '#0D2F5C'
const GOLD = '#C9A227'

const THEMES: { key: Theme; name: string; desc: string }[] = [
  { key: 'marine_center', name: 'Marine centré', desc: 'En-tête marine, logo centré, filet doré. Premium.' },
  { key: 'marine_band', name: 'Bandeau marine', desc: 'En-tête marine, logo à gauche. Corporate.' },
  { key: 'epure', name: 'Épuré clair', desc: 'En-tête blanc, logo en tuile, filet marine. Léger.' },
]

/** Mini-aperçu d'e-mail (en-tête + corps + pied) selon le thème. */
function Preview({ theme }: { theme: Theme }) {
  const monoDark = (
    <div style={{ width: 26, height: 26, borderRadius: 999, background: 'rgba(255,255,255,.18)', color: '#fff', fontSize: 10, fontWeight: 700, lineHeight: '26px', textAlign: 'center' }}>LC</div>
  )
  const head = theme === 'epure' ? (
    <div style={{ background: '#fff', borderBottom: `3px solid ${NAVY}`, padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ width: 24, height: 24, borderRadius: 6, background: NAVY, color: '#fff', fontSize: 9, fontWeight: 700, lineHeight: '24px', textAlign: 'center' }}>LC</div>
      <div><div style={{ color: NAVY, fontSize: 11, fontWeight: 600 }}>Le Comptoir Immo</div><div style={{ color: '#64748b', fontSize: 9 }}>Gestion locative</div></div>
    </div>
  ) : theme === 'marine_band' ? (
    <div style={{ background: NAVY, padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
      {monoDark}
      <div><div style={{ color: '#fff', fontSize: 11, fontWeight: 600 }}>Le Comptoir Immo</div><div style={{ color: '#a9c2e8', fontSize: 9 }}>Gestion locative</div></div>
    </div>
  ) : (
    <div style={{ background: NAVY, borderBottom: `3px solid ${GOLD}`, padding: '10px', textAlign: 'center' }}>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 4 }}>{monoDark}</div>
      <div style={{ color: '#fff', fontSize: 11, fontWeight: 600 }}>Le Comptoir Immo</div>
      <div style={{ color: '#a9c2e8', fontSize: 8, letterSpacing: '.04em' }}>GESTION LOCATIVE</div>
    </div>
  )
  const foot = theme === 'epure'
    ? { background: '#f4f6fb', color: '#94a3b8' }
    : { background: NAVY, color: '#a9c2e8' }
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden', background: '#fff' }}>
      {head}
      <div style={{ padding: '10px', fontSize: 10, color: '#334155', lineHeight: 1.5 }}>
        <div style={{ fontWeight: 600, color: NAVY, marginBottom: 3 }}>Vos accès à votre espace</div>
        Bonjour Jean, votre espace est prêt…
      </div>
      <div style={{ ...foot, padding: '7px 10px', fontSize: 8, textAlign: 'center' }}>Le Comptoir Immo · Gestion locative</div>
    </div>
  )
}

export default function EmailThemePicker() {
  const user = useAuthStore(s => s.user)
  const setUser = useAuthStore(s => s.setUser)
  const current = (user?.email_theme as Theme) || 'marine_center'
  const [busy, setBusy] = useState<Theme | null>(null)

  const choose = async (theme: Theme) => {
    if (theme === current) return
    setBusy(theme)
    try {
      const { data } = await apiClient.patch<User>('/users/me', { email_theme: theme })
      setUser(data)
      toast.success('Apparence des e-mails mise à jour.')
    } catch { /* intercepteur */ } finally { setBusy(null) }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h2 className="text-base font-semibold text-gray-900">Apparence des e-mails</h2>
      <p className="text-sm text-gray-500 mt-1 mb-4">
        Choisissez la mise en page appliquée à tous vos e-mails (accès, avis, quittances, candidatures…).
        Votre logo (Mes informations) s'affiche dans l'en-tête s'il est renseigné.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {THEMES.map(t => {
          const active = current === t.key
          return (
            <button key={t.key} onClick={() => choose(t.key)} disabled={busy === t.key}
              className={`text-left rounded-xl border-2 p-3 transition-colors ${active ? 'border-blue-600 bg-blue-50/40' : 'border-gray-200 hover:border-gray-300'} disabled:opacity-60`}>
              <Preview theme={t.key} />
              <div className="flex items-center justify-between mt-2">
                <span className="text-sm font-semibold text-gray-900">{t.name}</span>
                {active && <span className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700"><Check size={13} /> Actif</span>}
              </div>
              <p className="text-xs text-gray-500 mt-0.5">{t.desc}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
