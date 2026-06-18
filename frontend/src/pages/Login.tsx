import { useState } from 'react'
import { BRAND } from '@/lib/brand'
import { useNavigate, Navigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Mail, Lock, ChevronRight } from 'lucide-react'
import { useAuthStore, roleHomePath } from '@/store/authStore'
import type { AccountType } from '@/store/authStore'
import SubscriptionModal from './SubscriptionModal'
import { LogoMark } from '@/components/common/Logo'
import { authApi } from '@/api/auth'

const ACCOUNT_TYPES: {
  id: AccountType
  icon: string
  label: string
  subtitle: string
  color: string
  activeColor: string
  activeBg: string
  placeholder: string
}[] = [
  {
    id: 'gestionnaire',
    icon: '🏢',
    label: 'Gestionnaire',
    subtitle: 'Administration & gestion',
    color: BRAND.navy,
    activeColor: BRAND.navy,
    activeBg: 'rgba(13, 47, 92, 0.07)',
    placeholder: 'gestionnaire@cabinet.fr',
  },
  {
    id: 'proprietaire',
    icon: '🔑',
    label: 'Propriétaire',
    subtitle: 'Suivi de vos biens',
    color: BRAND.navyLight,
    activeColor: BRAND.navyLight,
    activeBg: 'rgba(26, 74, 138, 0.07)',
    placeholder: 'proprietaire@email.fr',
  },
  {
    id: 'locataire',
    icon: '🏠',
    label: 'Locataire',
    subtitle: 'Votre espace locatif',
    color: '#2563EB',
    activeColor: '#2563EB',
    activeBg: 'rgba(37, 99, 235, 0.07)',
    placeholder: 'locataire@email.fr',
  },
]

const loginSchema = z.object({
  email: z.string().email('Adresse e-mail invalide'),
  password: z.string().min(1, 'Mot de passe requis'),
})

type LoginForm = z.infer<typeof loginSchema>

// Hauteurs des colonnes du bâtiment + états fenêtres — calculés une seule fois au module load
const BUILDING_HEIGHTS = [32, 48, 40, 56, 36, 44, 28]
const BUILDING_WINDOWS = BUILDING_HEIGHTS.map(h =>
  Array.from({ length: Math.floor(h / 16) * 2 }, () => Math.random() > 0.4)
)

// ── Panneau gauche — branding ─────────────────────────────────────────────────
const BRAND_CONTENT: Record<AccountType, { title: string; desc: string; features: string[] }> = {
  gestionnaire: {
    title: 'Gérez votre patrimoine\nen toute simplicité',
    desc: 'Pilotez l\'ensemble de votre portefeuille, automatisez vos tâches et suivez vos indicateurs en temps réel.',
    features: ['Avis d\'échéances automatiques', 'Suivi des paiements en temps réel', 'Documents & quittances PDF'],
  },
  proprietaire: {
    title: 'Suivez vos biens\nà tout moment',
    desc: 'Consultez le taux d\'occupation, les loyers perçus et les documents de vos logements depuis un seul espace.',
    features: ['Vue consolidée de vos biens', 'Revenus & historique locatif', 'Accès aux baux et documents'],
  },
  locataire: {
    title: 'Votre espace locatif\npersonnalisé',
    desc: 'Retrouvez vos avis d\'échéances, vos quittances et l\'historique de vos paiements en quelques clics.',
    features: ['Avis d\'échéances & rappels', 'Téléchargement des quittances', 'Accès à vos documents'],
  },
}

function BrandPanel({ accountType }: { accountType: AccountType }) {
  const content = BRAND_CONTENT[accountType]
  return (
    <div className="hidden lg:flex lg:w-[52%] relative flex-col justify-between overflow-hidden"
         style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}>

      {/* Motif géométrique subtil */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.04]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke="white" strokeWidth="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* Cercles décoratifs */}
      <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full opacity-10"
           style={{ background: 'radial-gradient(circle, #4A90D9, transparent)' }} />
      <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full opacity-10"
           style={{ background: 'radial-gradient(circle, #F07800, transparent)' }} />

      {/* Header : Logo */}
      <div className="relative z-10 px-12 pt-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
               style={{ background: BRAND.orange }}>
            <LogoMark size={26} className="text-white" />
          </div>
          <span className="text-white font-bold text-lg tracking-wide">Le Comptoir Immo</span>
        </div>
      </div>

      {/* Centre : Message principal */}
      <div className="relative z-10 px-12 py-8">
        {/* Illustration immeuble stylisée */}
        <div className="mb-10 flex items-end gap-1.5" aria-hidden="true">
          {BUILDING_HEIGHTS.map((h, i) => (
            <div
              key={i}
              className="rounded-t flex-1 opacity-80"
              style={{
                height: `${h}px`,
                background: i % 3 === 0
                  ? 'rgba(240, 120, 0, 0.7)'
                  : 'rgba(255,255,255,0.15)',
              }}
            >
              <div className="grid grid-cols-2 gap-0.5 p-1 mt-1">
                {BUILDING_WINDOWS[i].map((lit, j) => (
                  <div key={j} className="h-1.5 rounded-sm"
                       style={{ background: lit ? 'rgba(255,220,100,0.6)' : 'rgba(255,255,255,0.1)' }} />
                ))}
              </div>
            </div>
          ))}
        </div>

        <h1 className="text-white text-3xl font-bold leading-snug mb-4">
          {content.title.split('\n').map((line, i) => (
            i === 0
              ? <span key={i}>{line}<br /></span>
              : <span key={i} style={{ color: BRAND.orange }}>{line}</span>
          ))}
        </h1>
        <p className="text-blue-200 text-sm leading-relaxed max-w-xs">
          {content.desc}
        </p>

        {/* Features */}
        <div className="mt-8 space-y-3">
          {content.features.map((feat) => (
            <div key={feat} className="flex items-center gap-2.5">
              <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                   style={{ background: 'rgba(240, 120, 0, 0.25)', border: '1px solid rgba(240,120,0,0.5)' }}>
                <ChevronRight size={10} className="text-orange-300" />
              </div>
              <span className="text-blue-100 text-sm">{feat}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="relative z-10 px-12 pb-10">
        <p className="text-blue-300 text-xs">
          © {new Date().getFullYear()} Le Comptoir Immo · Gestion locative professionnelle
        </p>
      </div>
    </div>
  )
}

// ── Panneau droit — formulaire ────────────────────────────────────────────────
export default function Login() {
  const navigate = useNavigate()
  const { login, isLoading, isAuthenticated, user } = useAuthStore()

  // ── Tous les hooks AVANT tout early return (règle React) ──────────────────
  const [error, setError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [accountType, setAccountType] = useState<AccountType>('gestionnaire')
  const [showSubscribe, setShowSubscribe] = useState(false)
  const [showForgot, setShowForgot] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)
  const [forgotDone, setForgotDone] = useState(false)
  const [forgotError, setForgotError] = useState<string | null>(null)

  const activeType = ACCOUNT_TYPES.find(t => t.id === accountType)!

  const { register, handleSubmit, reset, getValues, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const openForgot = () => {
    setForgotEmail(getValues('email') || '')
    setForgotDone(false)
    setForgotError(null)
    setShowForgot(true)
  }

  const submitForgot = async () => {
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(forgotEmail.trim())) {
      setForgotError('Adresse e-mail invalide')
      return
    }
    setForgotLoading(true)
    setForgotError(null)
    try {
      await authApi.forgotPassword(forgotEmail.trim())
      setForgotDone(true)
    } catch {
      // Réponse générique côté serveur : en cas d'erreur réseau on reste neutre.
      setForgotDone(true)
    } finally {
      setForgotLoading(false)
    }
  }

  // Déjà connecté → redirect immédiat vers la page d'accueil du rôle
  if (isAuthenticated && user) {
    return <Navigate to={roleHomePath(user.role)} replace />
  }

  const onSubmit = async (data: LoginForm) => {
    setError(null)
    try {
      // La validation du rôle est faite dans le store AVANT que isAuthenticated=true
      // → pas de race condition avec le early-return <Navigate>
      const rolePath = await login(data.email, data.password, accountType)
      navigate(rolePath, { replace: true })
    } catch (err: any) {
      // Distingue : rôle invalide / mauvais identifiants / API injoignable / erreur serveur.
      // Important : ne PAS afficher "Email ou mot de passe incorrect" quand l'API est down,
      // sinon l'utilisateur cherche un mauvais mot de passe alors que le serveur ne répond pas.
      let msg: string
      if (err?.code === 'ROLE_MISMATCH') {
        msg = err.message
      } else {
        const status = err?.response?.status as number | undefined
        const detail = err?.response?.data?.detail as string | undefined
        if (status === 401 || status === 403) {
          msg = detail || 'Email ou mot de passe incorrect'
        } else if (status === 429) {
          msg = 'Trop de tentatives. Réessayez dans quelques instants.'
        } else if (status === 502 || status === 503 || status === 504) {
          msg = "Service momentanément indisponible : le serveur redémarre ou est en maintenance. Réessayez dans quelques instants."
        } else if (status && status >= 500) {
          msg = detail || "Une erreur est survenue côté serveur. Réessayez plus tard."
        } else if (!err?.response) {
          // Pas de réponse HTTP : réseau coupé, CORS, ou backend injoignable
          msg = "Impossible de joindre le serveur. Vérifiez votre connexion ou réessayez dans quelques instants."
        } else {
          msg = detail || 'Email ou mot de passe incorrect'
        }
      }
      setError(msg)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* Panneau gauche : visible uniquement desktop */}
      <BrandPanel accountType={accountType} />

      {/* Panneau droit : formulaire */}
      <div className="flex-1 flex flex-col justify-center items-center bg-white px-6 py-12 lg:px-16">

        {/* Logo mobile uniquement */}
        <div className="lg:hidden mb-10 text-center">
          <div className="inline-flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                 style={{ background: BRAND.navy }}>
              <LogoMark size={24} className="text-white" />
            </div>
            <span className="font-bold text-lg" style={{ color: BRAND.navy }}>Le Comptoir Immo</span>
          </div>
        </div>

        {/* Formulaire centré */}
        <div className="w-full max-w-[400px]">

          {/* Titre */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold mb-1" style={{ color: BRAND.navy }}>
              Connexion
            </h2>
            <p className="text-sm text-gray-500">
              {activeType.subtitle}
            </p>
          </div>

          {/* Sélecteur de type de compte */}
          <div className="mb-6">
            <p className="text-xs font-medium mb-2.5" style={{ color: '#64748B' }}>
              Je suis…
            </p>
            <div className="grid grid-cols-3 gap-2">
              {ACCOUNT_TYPES.map(type => {
                const isActive = accountType === type.id
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => { setAccountType(type.id); setError(null); reset({ email: '', password: '' }) }}
                    className="flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl transition-all text-center"
                    style={{
                      border: isActive
                        ? `1.5px solid ${type.activeColor}`
                        : '1.5px solid #E2E8F0',
                      background: isActive ? type.activeBg : '#F8FAFC',
                      boxShadow: isActive
                        ? `0 0 0 3px ${type.activeBg}`
                        : 'none',
                    }}
                  >
                    <span className="text-xl leading-none">{type.icon}</span>
                    <span
                      className="text-xs font-semibold leading-tight"
                      style={{ color: isActive ? type.activeColor : '#64748B' }}
                    >
                      {type.label}
                    </span>
                    {isActive && (
                      <span
                        className="w-1.5 h-1.5 rounded-full mt-0.5"
                        style={{ background: type.activeColor }}
                      />
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Erreur globale */}
          {error && (
            <div className="mb-5 flex items-start gap-2.5 p-3.5 rounded-xl text-sm"
                 style={{ background: '#FFF1F0', border: '1px solid #FFCCC7', color: '#CF1322' }}>
              <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>

            {/* Champ Email */}
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: '#1A2F4E' }}>
                Adresse e-mail
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                  <Mail size={16} className={errors.email ? 'text-red-400' : 'text-gray-400'} />
                </div>
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  spellCheck={false}
                  placeholder={activeType.placeholder}
                  className="w-full pl-10 pr-4 py-3 text-sm rounded-xl transition-all outline-none"
                  style={{
                    border: errors.email ? '1.5px solid #FF4D4F' : '1.5px solid #E2E8F0',
                    background: errors.email ? '#FFF1F0' : '#F8FAFC',
                    color: '#1A2F4E',
                  }}
                  onFocus={e => {
                    if (!errors.email) {
                      e.target.style.border = '1.5px solid #0D2F5C'
                      e.target.style.background = '#FFFFFF'
                      e.target.style.boxShadow = '0 0 0 3px rgba(13, 47, 92, 0.08)'
                    }
                  }}
                  onBlur={e => {
                    if (!errors.email) {
                      e.target.style.border = '1.5px solid #E2E8F0'
                      e.target.style.background = '#F8FAFC'
                      e.target.style.boxShadow = 'none'
                    }
                  }}
                />
              </div>
              {errors.email && (
                <p className="mt-1.5 text-xs" style={{ color: '#CF1322' }}>{errors.email.message}</p>
              )}
            </div>

            {/* Champ Mot de passe */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm font-medium" style={{ color: '#1A2F4E' }}>
                  Mot de passe
                </label>
                <button
                  type="button"
                  onClick={openForgot}
                  className="text-xs font-medium hover:underline"
                  style={{ color: BRAND.orange }}
                >
                  Mot de passe oublié ?
                </button>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                  <Lock size={16} className={errors.password ? 'text-red-400' : 'text-gray-400'} />
                </div>
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full pl-10 pr-11 py-3 text-sm rounded-xl transition-all outline-none"
                  style={{
                    border: errors.password ? '1.5px solid #FF4D4F' : '1.5px solid #E2E8F0',
                    background: errors.password ? '#FFF1F0' : '#F8FAFC',
                    color: '#1A2F4E',
                  }}
                  onFocus={e => {
                    if (!errors.password) {
                      e.target.style.border = '1.5px solid #0D2F5C'
                      e.target.style.background = '#FFFFFF'
                      e.target.style.boxShadow = '0 0 0 3px rgba(13, 47, 92, 0.08)'
                    }
                  }}
                  onBlur={e => {
                    if (!errors.password) {
                      e.target.style.border = '1.5px solid #E2E8F0'
                      e.target.style.background = '#F8FAFC'
                      e.target.style.boxShadow = 'none'
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs" style={{ color: '#CF1322' }}>{errors.password.message}</p>
              )}
            </div>

            {/* Bouton */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3.5 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
              style={{
                background: isLoading
                  ? '#5589C4'
                  : 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)',
                boxShadow: isLoading ? 'none' : '0 4px 15px rgba(13, 47, 92, 0.3)',
              }}
              onMouseEnter={e => {
                if (!isLoading) {
                  (e.currentTarget as HTMLButtonElement).style.background =
                    'linear-gradient(135deg, #0A2448 0%, #163F78 100%)'
                  ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                    '0 6px 20px rgba(13, 47, 92, 0.4)'
                }
              }}
              onMouseLeave={e => {
                if (!isLoading) {
                  (e.currentTarget as HTMLButtonElement).style.background =
                    'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)'
                  ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                    '0 4px 15px rgba(13, 47, 92, 0.3)'
                }
              }}
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Connexion en cours…
                </>
              ) : (
                <>
                  Se connecter
                  <ChevronRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Mention sécurité */}
          <div className="mt-7 pt-5 border-t border-gray-100 flex items-center justify-center gap-1.5">
            <svg className="w-3.5 h-3.5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span className="text-xs text-gray-400">Connexion sécurisée · Espace {activeType.label}</span>
          </div>

          {/* CTA souscription : discret, sans dénaturer la page */}
          <p className="mt-4 text-center text-xs text-gray-400">
            Pas encore client ?{' '}
            <button type="button" onClick={() => setShowSubscribe(true)}
              className="font-medium hover:underline" style={{ color: BRAND.orange }}>
              Demander une démo
            </button>
          </p>
        </div>

        {/* Footer mobile */}
        <div className="lg:hidden mt-10 text-center">
          <p className="text-xs text-gray-400">
            © {new Date().getFullYear()} Le Comptoir Immo · Gestion locative
          </p>
        </div>
      </div>

      <SubscriptionModal open={showSubscribe} onClose={() => setShowSubscribe(false)} />

      {/* « Mot de passe oublié ? » : réinitialisation en libre-service par e-mail */}
      {showForgot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
             onClick={() => setShowForgot(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
               onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-2" style={{ color: BRAND.navy }}>
              Mot de passe oublié&nbsp;?
            </h3>

            {forgotDone ? (
              <>
                <div className="mb-2 flex items-start gap-2.5 p-3.5 rounded-xl text-sm"
                     style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', color: '#15803D' }}>
                  <span>
                    Si un compte est associé à cette adresse, vous allez recevoir un e-mail
                    contenant un mot de passe temporaire. Pensez à vérifier vos courriers indésirables.
                  </span>
                </div>
                <div className="mt-5 flex justify-end">
                  <button type="button" onClick={() => setShowForgot(false)}
                    className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
                    style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}>
                    Fermer
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="text-sm text-gray-600 leading-relaxed">
                  Saisissez votre adresse e-mail&nbsp;: vous recevrez un <span className="font-semibold">mot de
                  passe temporaire</span> pour vous reconnecter. Il vous sera demandé d'en choisir
                  un nouveau dès la connexion.
                </p>
                {forgotError && (
                  <p className="mt-3 text-xs" style={{ color: '#CF1322' }}>{forgotError}</p>
                )}
                <div className="mt-4 relative">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                    <Mail size={16} className="text-gray-400" />
                  </div>
                  <input
                    type="email"
                    autoFocus
                    value={forgotEmail}
                    onChange={e => setForgotEmail(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') submitForgot() }}
                    placeholder="votre@email.fr"
                    className="w-full pl-10 pr-4 py-3 text-sm rounded-xl outline-none"
                    style={{ border: '1.5px solid #E2E8F0', background: '#F8FAFC', color: '#1A2F4E' }}
                  />
                </div>
                <p className="mt-3 text-xs text-gray-400">
                  Pour votre sécurité, votre mot de passe actuel n'est jamais communiqué&nbsp;: nous en
                  générons un nouveau, temporaire.
                </p>
                <div className="mt-5 flex justify-end gap-3">
                  <button type="button" onClick={() => setShowForgot(false)}
                    className="px-4 py-2.5 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-100">
                    Annuler
                  </button>
                  <button type="button" onClick={submitForgot} disabled={forgotLoading}
                    className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
                    style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}>
                    {forgotLoading ? 'Envoi…' : 'Recevoir un accès temporaire'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
