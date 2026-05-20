import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, Building2, FileText,
  CreditCard, Bell, Settings, LogOut, ChevronRight
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord' },
  { to: '/tenants', icon: Users, label: 'Locataires' },
  { to: '/properties', icon: Building2, label: 'Biens immobiliers' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
  { to: '/admin', icon: Settings, label: 'Administration', adminOnly: true },
]

export function Sidebar() {
  const { user, logout } = useAuthStore()

  const filteredItems = navItems.filter(
    (item) => !item.adminOnly || user?.role === 'admin'
  )

  return (
    <aside className="w-64 min-h-screen bg-gray-900 flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">L</span>
          </div>
          <div>
            <p className="text-white font-semibold text-sm">Locataire Cloud</p>
            <p className="text-gray-400 text-xs">Gestion locative</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {filteredItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info + logout */}
      <div className="px-3 py-4 border-t border-gray-700">
        <div className="px-3 py-2 mb-2">
          <p className="text-white text-sm font-medium truncate">{user?.full_name}</p>
          <p className="text-gray-400 text-xs truncate">{user?.email}</p>
          <span className="inline-block mt-1 px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded-full capitalize">
            {user?.role}
          </span>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <LogOut size={18} />
          <span>Déconnexion</span>
        </button>
      </div>
    </aside>
  )
}
