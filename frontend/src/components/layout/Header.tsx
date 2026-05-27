import { Bell, User, LogOut, ChevronDown } from 'lucide-react'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { notificationsApi } from '@/api/notifications'

const POLL_INTERVAL_MS = 30_000 // 30 secondes

// ── Header principal ──────────────────────────────────────────────────────────

export function Header() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [unreadCount, setUnreadCount] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)
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

  // Refresh sur montage, changement de route, et toutes les 30s
  useEffect(() => {
    if (!user) return
    fetchCount()
  }, [user, fetchCount, location.pathname])

  useEffect(() => {
    if (!user) return
    const timer = setInterval(fetchCount, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [user, fetchCount])

  useEffect(() => {
    window.addEventListener('notification-read', fetchCount)
    return () => window.removeEventListener('notification-read', fetchCount)
  }, [fetchCount])

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

  const handleLogout = () => {
    setMenuOpen(false)
    logout()
    navigate('/login')
  }

  const initials = user?.full_name?.charAt(0).toUpperCase() ?? '?'

  return (
    <header className="h-14 bg-white border-b border-gray-200 px-6 flex items-center justify-between no-print">
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
                  onClick={() => { setMenuOpen(false); navigate('/profil') }}
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
  )
}
