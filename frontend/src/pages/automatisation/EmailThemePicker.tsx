import { useState } from 'react'
import { Check } from 'lucide-react'
import { apiClient } from '@/api/client'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'
import type { User } from '@/types/auth'

type Theme = 'marine_center' | 'marine_band' | 'epure' | 'teal_band' | 'epure_center'

const NAVY = '#0D2F5C'
const GOLD = '#C9A227'
const TEAL = '#1F7A6B'

const THEMES: { key: Theme; name: string; desc: string }[] = [
  { key: 'marine_center', name: 'Marine centré', desc: 'En-tête marine, logo centré, filet doré. Premium.' },
  { key: 'marine_band', name: 'Bandeau marine', desc: 'En-tête marine, logo à gauche. Corporate.' },
  { key: 'teal_band', name: 'Bandeau sarcelle', desc: 'En-tête vert sarcelle de marque, logo à gauche.' },
  { key: 'epure_center', name: 'Épuré centré', desc: 'En-tête blanc, logo centré, filet doré. Élégant.' },
  { key: 'epure', name: 'Épuré clair', desc: 'En-tête blanc, logo à gauche, filet marine. Léger.' },
]

function Medallion({ onDark, logoUrl, dim = 26 }: { onDark: boolean; logoUrl?: string | null; dim?: number }) {
  if (logoUrl) {
    return <div style={{ width: dim, height: dim, borderRadius: 6, background: '#fff', padding: 2, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
      <img src={logoUrl} alt="" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
    </div>
  }
  const style: React.CSSProperties = onDark
    ? { width: dim, height: dim, borderRadius: 999, background: 'rgba(255,255,255,.18)', color: '#fff' }
    : { width: dim, height: dim, borderRadius: 6, background: NAVY, color: '#fff' }
  return <div style={{ ...style, fontSize: dim * 0.38, fontWeight: 700, lineHeight: `${dim}px`, textAlign: 'center' }}>LC</div>
}

/** Mini-aperçu d'e-mail (en-tête + corps + pied) selon le thème, avec le logo + nom de compte réels. */
function Preview({ theme, logoUrl, brand }: { theme: Theme; logoUrl?: string | null; brand: string }) {
  const bandLeft = (bg: string, sub: string) => (
    <div style={{ background: bg, padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
      <Medallion onDark logoUrl={logoUrl} />
      <div><div style={{ color: '#fff', fontSize: 11, fontWeight: 600 }}>{brand}</div><div style={{ color: sub, fontSize: 9 }}>Gestion locative</div></div>
    </div>
  )
  let head: React.ReactNode
  if (theme === 'epure') head = (
    <div style={{ background: '#fff', borderBottom: `3px solid ${NAVY}`, padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
      <Medallion onDark={false} logoUrl={logoUrl} />
      <div><div style={{ color: NAVY, fontSize: 11, fontWeight: 600 }}>{brand}</div><div style={{ color: '#64748b', fontSize: 9 }}>Gestion locative</div></div>
    </div>
  )
  else if (theme === 'epure_center') head = (
    <div style={{ background: '#fff', borderBottom: `3px solid ${GOLD}`, padding: '10px', textAlign: 'center' }}>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 4 }}><Medallion onDark={false} logoUrl={logoUrl} /></div>
      <div style={{ color: NAVY, fontSize: 11, fontWeight: 600 }}>{brand}</div>
      <div style={{ color: '#94a3b8', fontSize: 8, letterSpacing: '.04em' }}>GESTION LOCATIVE</div>
    </div>
  )
  else if (theme === 'marine_band') head = bandLeft(NAVY, '#a9c2e8')
  else if (theme === 'teal_band') head = bandLeft(TEAL, '#cdeae3')
  else head = (
    <div style={{ background: NAVY, borderBottom: `3px solid ${GOLD}`, padding: '10px', textAlign: 'center' }}>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 4 }}><Medallion onDark logoUrl={logoUrl} /></div>
      <div style={{ color: '#fff', fontSize: 11, fontWeight: 600 }}>{brand}</div>
      <div style={{ color: '#a9c2e8', fontSize: 8, letterSpacing: '.04em' }}>GESTION LOCATIVE</div>
    </div>
  )
  const foot = theme === 'epure' || theme === 'epure_center'
    ? { background: '#f4f6fb', color: '#94a3b8' }
    : theme === 'teal_band' ? { background: TEAL, color: '#cdeae3' } : { background: NAVY, color: '#a9c2e8' }
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden', background: '#fff' }}>
      {head}
      <div style={{ padding: '10px', fontSize: 10, color: '#334155', lineHeight: 1.5 }}>
        <div style={{ fontWeight: 600, color: NAVY, marginBottom: 3 }}>Vos accès à votre espace</div>
        Bonjour Jean, votre espace est prêt…
      </div>
      <div style={{ ...foot, padding: '7px 10px', fontSize: 8, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{brand} · Gestion locative</div>
    </div>
  )
}

export default function EmailThemePicker() {
  const user = useAuthStore(s => s.user)
  const setUser = useAuthStore(s => s.setUser)
  const current = (user?.email_theme as Theme) || 'marine_center'
  const logoUrl = user?.logo_url || null
  const brand = (user?.full_name || '').trim() || 'Le Comptoir Immo'
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
        {logoUrl
          ? ' Les aperçus montrent votre logo tel qu’il apparaîtra dans l’en-tête.'
          : ' Ajoutez un logo dans « Mes informations » pour l’afficher dans l’en-tête (un monogramme « LC » est utilisé à défaut).'}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {THEMES.map(t => {
          const active = current === t.key
          return (
            <button key={t.key} onClick={() => choose(t.key)} disabled={busy === t.key}
              className={`text-left rounded-xl border-2 p-3 transition-colors ${active ? 'border-blue-600 bg-blue-50/40' : 'border-gray-200 hover:border-gray-300'} disabled:opacity-60`}>
              <Preview theme={t.key} logoUrl={logoUrl} brand={brand} />
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
