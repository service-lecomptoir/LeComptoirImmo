import { Bell, User, LogOut, ChevronDown, X, Check, Eye, EyeOff } from 'lucide-react'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { notificationsApi } from '@/api/notifications'
import { apiClient } from '@/api/client'

const POLL_INTERVAL_MS = 60_000 // 1 minute

// ── Modale "Mon profil" ───────────────────────────────────────────────────────

interface ProfileModalProps {
  user: { full_name: string; email: string } | null
  onClose: () => void
  onSaved: (updated: { full_name: string; email: string }) => void
}

function ProfileModal({ user, onClose, onSaved }: ProfileModalProps) {
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const handleSaveProfile = async () => {
    if (!fullName.trim()) { setError('Le nom complet est requis.'); return }
    setIsSaving(true)
    setError(null)
    try {
      const { data } = await apiClient.patch('/users/me', {
        full_name: fullName.trim(),
        email: email.trim() || undefined,
      })
      onSaved({ full_name: data.full_name, email: data.email })
      setSuccessMsg('Profil mis à jour avec succès !')
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Erreur lors de la mise à jour.'
      setError(msg)
    } finally {
      setIsSaving(false)
    }
  }

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword) { setError('Remplissez les deux champs de mot de passe.'); return }
    if (newPassword.length < 8) { setError('Le nouveau mot de passe doit contenir au moins 8 caractères.'); return }
    setIsSaving(true)
    setError(null)
    try {
      await apiClient.patch('/users/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setSuccessMsg('Mot de passe modifié avec succès !')
      setCurrentPassword('')
      setNewPassword('')
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Mot de passe actuel incorrect.'
      setError(msg)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-base font-semibold text-gray-800">Mon profil</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors">
            <X size={16} className="text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Avatar */}
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-700 text-xl font-bold">
                {fullName.charAt(0).toUpperCase() || '?'}
              </span>
            </div>
            <div>
              <p className="font-semibold text-gray-800">{fullName || '—'}</p>
              <p className="text-sm text-gray-500">{email}</p>
            </div>
          </div>

          {/* Bandeau retour */}
          {successMsg && (
            <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              <Check size={14} /> {successMsg}
            </div>
          )}
          {error && (
            <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {/* ── Informations ── */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Informations personnelles
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Nom complet</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={e => { setFullName(e.target.value); setSuccessMsg(null); setError(null) }}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Identifiant (adresse e-mail)</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => { setEmail(e.target.value); setSuccessMsg(null); setError(null) }}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={handleSaveProfile}
                disabled={isSaving}
                className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
              >
                {isSaving ? 'Enregistrement…' : 'Enregistrer'}
              </button>
            </div>
          </div>

          {/* ── Mot de passe ── */}
          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Changer le mot de passe
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Mot de passe actuel</label>
                <div className="relative">
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={e => { setCurrentPassword(e.target.value); setSuccessMsg(null); setError(null) }}
                    className="w-full px-3 py-2 pr-9 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPwd(v => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Nouveau mot de passe</label>
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={newPassword}
                  onChange={e => { setNewPassword(e.target.value); setSuccessMsg(null); setError(null) }}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="••••••••  (8 caractères min.)"
                />
              </div>
              <button
                onClick={handleChangePassword}
                disabled={isSaving || !currentPassword || !newPassword}
                className="w-full py-2 rounded-lg bg-gray-800 text-white text-sm font-medium hover:bg-gray-900 disabled:opacity-50 transition-colors"
              >
                {isSaving ? 'Modification…' : 'Modifier le mot de passe'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Header principal ──────────────────────────────────────────────────────────

export function Header() {
  const { user, logout, fetchMe } = useAuthStore()
  const navigate = useNavigate()
  const [unreadCount, setUnreadCount] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // ── Notifications ─────────────────────────────────────────────────────────
  const fetchCount = useCallback(async () => {
    try {
      const { data } = await notificationsApi.getBadgeCount()
      setUnreadCount(data.total)
    } catch {
      // silently ignore
    }
  }, [])

  useEffect(() => {
    if (!user) return
    fetchCount()
    const timer = setInterval(fetchCount, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [user, fetchCount])

  // ── Fermer le menu au clic extérieur ──────────────────────────────────────
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    if (menuOpen) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  // ── Déconnexion ───────────────────────────────────────────────────────────
  const handleLogout = () => {
    setMenuOpen(false)
    logout()
    navigate('/login')
  }

  // ── Profil sauvegardé ─────────────────────────────────────────────────────
  const handleProfileSaved = () => {
    // Recharger le profil depuis l'API
    fetchMe()
    setShowProfile(false)
  }

  const initials = user?.full_name?.charAt(0).toUpperCase() ?? '?'

  return (
    <>
      <header className="h-14 bg-white border-b border-gray-200 px-6 flex items-center justify-between">
        <div />
        <div className="flex items-center gap-3">
          {/* Notifications */}
          <button
            onClick={() => navigate('/notifications')}
            className={`relative p-2 rounded-lg transition-colors ${
              unreadCount > 0
                ? 'text-blue-600 bg-blue-50 hover:bg-blue-100'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
            title="Notifications"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none animate-pulse">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {/* Avatar + dropdown */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(v => !v)}
              className="flex items-center gap-1.5 px-1.5 py-1 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-700 text-sm font-semibold">{initials}</span>
              </div>
              <ChevronDown
                size={14}
                className={`text-gray-400 transition-transform ${menuOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {menuOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden z-50">
                {/* Info utilisateur */}
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                  <p className="text-sm font-semibold text-gray-800 truncate">{user?.full_name}</p>
                  <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                </div>

                {/* Actions */}
                <div className="py-1">
                  <button
                    onClick={() => { setMenuOpen(false); setShowProfile(true) }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <User size={15} className="text-gray-400" />
                    Mon profil
                  </button>
                  <div className="border-t border-gray-100 my-1" />
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <LogOut size={15} className="text-red-400" />
                    Déconnexion
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Modale profil */}
      {showProfile && (
        <ProfileModal
          user={user}
          onClose={() => setShowProfile(false)}
          onSaved={handleProfileSaved}
        />
      )}
    </>
  )
}
