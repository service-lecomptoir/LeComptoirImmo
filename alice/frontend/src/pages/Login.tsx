import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, ChevronRight, Shield } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export default function Login() {
  const navigate = useNavigate()
  const { login, isLoading, isAuthenticated } = useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await login(email, password)
      navigate('/dashboard', { replace: true })
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      const msg = axiosError?.response?.data?.detail || 'Email ou mot de passe incorrect'
      setError(msg)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* Panneau gauche — branding */}
      <div
        className="hidden lg:flex lg:w-[48%] flex-col justify-between overflow-hidden"
        style={{ background: 'linear-gradient(145deg, #312e81 0%, #4338ca 50%, #4f46e5 100%)' }}
      >
        {/* Motif géométrique */}
        <svg className="absolute inset-0 w-full h-full opacity-[0.04] pointer-events-none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="white" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>

        {/* Cercles décoratifs */}
        <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full opacity-10"
             style={{ background: 'radial-gradient(circle, #818cf8, transparent)' }} />
        <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full opacity-10"
             style={{ background: 'radial-gradient(circle, #c4b5fd, transparent)' }} />

        {/* Header — Logo */}
        <div className="relative z-10 px-12 pt-12">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-400 flex items-center justify-center">
              <span className="text-white font-bold text-sm">PG</span>
            </div>
            <span className="text-white font-bold text-lg tracking-wide">Alice</span>
          </div>
        </div>

        {/* Centre */}
        <div className="relative z-10 px-12 py-8">
          <div className="mb-10">
            <Shield size={48} className="text-indigo-300 opacity-80" />
          </div>
          <h1 className="text-white text-3xl font-bold leading-snug mb-4">
            Administration SaaS<br />
            <span className="text-indigo-300">Le Comptoir Immo</span>
          </h1>
          <p className="text-indigo-200 text-sm leading-relaxed max-w-xs">
            Gérez les comptes gestionnaires, les formules tarifaires et les licences depuis un espace centralisé.
          </p>

          <div className="mt-8 space-y-3">
            {['Gestion des licences gestionnaires', 'Blocage cascade propriétaires & locataires', 'Plans tarifaires flexibles'].map((feat) => (
              <div key={feat} className="flex items-center gap-2.5">
                <div className="w-5 h-5 rounded-full bg-indigo-400/30 border border-indigo-400/50 flex items-center justify-center flex-shrink-0">
                  <ChevronRight size={10} className="text-indigo-200" />
                </div>
                <span className="text-indigo-100 text-sm">{feat}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 px-12 pb-10">
          <p className="text-indigo-400 text-xs">
            &copy; {new Date().getFullYear()} Alice &middot; Espace super-administrateur
          </p>
        </div>
      </div>

      {/* Panneau droit — formulaire */}
      <div className="flex-1 flex flex-col justify-center items-center bg-white px-6 py-12 lg:px-16">

        {/* Logo mobile */}
        <div className="lg:hidden mb-10 text-center">
          <div className="inline-flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
              <span className="text-white font-bold text-xs">PG</span>
            </div>
            <span className="font-bold text-lg text-indigo-900">Alice</span>
          </div>
        </div>

        <div className="w-full max-w-[400px]">
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-1 text-indigo-900">Connexion</h2>
            <p className="text-sm text-gray-500">Espace super-administrateur</p>
          </div>

          {/* Erreur */}
          {error && (
            <div className="mb-5 flex items-start gap-2.5 p-3.5 rounded-xl text-sm bg-red-50 border border-red-200 text-red-700">
              <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {/* Email */}
            <div>
              <label className="block text-sm font-medium mb-1.5 text-indigo-900">
                Adresse e-mail
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                  <Mail size={16} className="text-gray-400" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="superadmin@alice.fr"
                  className="w-full pl-10 pr-4 py-3 text-sm rounded-xl border border-gray-200 bg-gray-50 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 focus:bg-white transition-all"
                  required
                />
              </div>
            </div>

            {/* Mot de passe */}
            <div>
              <label className="block text-sm font-medium mb-1.5 text-indigo-900">
                Mot de passe
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                  <Lock size={16} className="text-gray-400" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full pl-10 pr-11 py-3 text-sm rounded-xl border border-gray-200 bg-gray-50 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 focus:bg-white transition-all"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Bouton */}
            <button
              type="submit"
              disabled={isLoading || !email || !password}
              className="w-full py-3.5 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 transition-all disabled:opacity-60 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-700 shadow-lg shadow-indigo-200"
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

          <div className="mt-7 pt-5 border-t border-gray-100 flex items-center justify-center gap-1.5">
            <Shield size={12} className="text-gray-300" />
            <span className="text-xs text-gray-400">Accès restreint aux super-administrateurs</span>
          </div>
        </div>
      </div>
    </div>
  )
}
