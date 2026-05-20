import { Bell } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export function Header() {
  const { user } = useAuthStore()

  return (
    <header className="h-14 bg-white border-b border-gray-200 px-6 flex items-center justify-between">
      <div />
      <div className="flex items-center gap-3">
        {/* Notifications badge */}
        <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
          <Bell size={18} />
          {/* Badge — Phase 7 */}
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
