import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, Building2, FileText,
  CreditCard, Bell, Settings, LogOut, Calendar,
  Home, Receipt,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import type { Role } from '@/types/auth'
import clsx from 'clsx'

interface NavItem {
  to: string
  icon: React.ElementType
  label: string
  roles?: Role[]   // undefined = tous les rôles
}

// Navigation Gestionnaire / Admin
const navGestionnaire: NavItem[] = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord' },
  { to: '/tenants', icon: Users, label: 'Locataires' },
  { to: '/properties', icon: Building2, label: 'Biens immobiliers' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/avis-echeances', icon: Calendar, label: 'Avis d\'échéances' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
  { to: '/admin', icon: Settings, label: 'Administration', roles: ['admin'] },
]

// Navigation Propriétaire
const navProprietaire: NavItem[] = [
  { to: '/proprietaire', icon: LayoutDashboard, label: 'Mon tableau de bord' },
  { to: '/proprietaire/biens', icon: Building2, label: 'Mes biens' },
  { to: '/proprietaire/revenus', icon: CreditCard, label: 'Mes revenus' },
  { to: '/proprietaire/locataires', icon: Users, label: 'Mes locataires' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
]

// Navigation Locataire
const navLocataire: NavItem[] = [
  { to: '/locataire', icon: Home, label: 'Mon espace' },
  { to: '/locataire/avis-echeances', icon: Calendar, label: 'Avis d\'échéances' },
  { to: '/locataire/paiements', icon: CreditCard, label: 'Mes paiements' },
  { to: '/locataire/documents', icon: Receipt, label: 'Mes documents' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
]

const ROLE_LABEL: Record<Role, string> = {
  admin: 'Administrateur',
  gestionnaire: 'Gestionnaire',
  proprietaire: 'Propriétaire',
  locataire: 'Locataire',
  lecture: 'Lecture seule',
  comptable: 'Comptable',
}

export function Sidebar() {
  const { user, logout } = useAuthStore()

  const getNavItems = (): NavItem[] => {
    if (!user) return []
    if (user.role === 'locataire') return navLocataire
    if (user.role === 'proprietaire') return navProprietaire
    return navGestionnaire
  }

  const filteredItems = getNavItems().filter(
    (item) => !item.roles || item.roles.includes(user?.role as Role)
  )

  return (
    <aside className="w-64 min-h-screen bg-gray-900 flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xs">LC</span>
          </div>
          <div>
            <p className="text-white font-semibold text-sm">LeComptoirImmo</p>
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
            end={to === '/proprietaire' || to === '/locataire'}
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
          <span className="inline-block mt-1 px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded-full">
            {ROLE_LABEL[user?.role as Role] ?? user?.role}
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
