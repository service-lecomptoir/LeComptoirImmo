import { Bell } from 'lucide-react'
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { notificationsApi } from '@/api/notifications'

const POLL_INTERVAL_MS = 60_000 // 1 minute

export function Header() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [unreadCount, setUnreadCount] = useState(0)

  const fetchCount = useCallback(async () => {
    try {
      const { data } = await notificationsApi.getUnreadCount()
      setUnreadCount(data.count)
    } catch {
      // silently ignore (network, auth issues)
    }
  }, [])

  useEffect(() => {
    if (!user) return
    fetchCount()
    const timer = setInterval(fetchCount, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [user, fetchCount])

  return (
    <header className="h-14 bg-white border-b border-gray-200 px-6 flex items-center justify-between">
      <div />
      <div className="flex items-center gap-3">
        {/* Notifications badge */}
        <button
          onClick={() => navigate('/notifications')}
          className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          title="Notifications"
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>

        {/* Avatar */}
        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
          <span className="text-blue-700 text-sm font-semibold">
            {user?.full_name?.charAt(0).toUpperCase()}
          </span>
        </div>
      </div>
    </header>
  )
}
