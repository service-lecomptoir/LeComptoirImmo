import { useEffect, useState, useCallback } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, CreditCard, FileText, Inbox, X } from 'lucide-react'
import clsx from 'clsx'
import { subscriptionsApi } from '@/api/subscriptions'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/gestionnaires', icon: Users, label: 'Gestionnaires' },
  { to: '/plans', icon: CreditCard, label: 'Plans tarifaires' },
  { to: '/factures', icon: FileText, label: 'Factures' },
  { to: '/demandes', icon: Inbox, label: 'Demandes' },
]

const POLL_MS = 60000

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const [newLeads, setNewLeads] = useState(0)
  const location = useLocation()

  const refresh = useCallback(async () => {
    try {
      const { data } = await subscriptionsApi.stats()
      setNewLeads(data.nouveau ?? 0)
    } catch {
      /* silencieux */
    }
  }, [])

  // Au montage, à chaque navigation, et toutes les 60 s
  useEffect(() => { refresh() }, [refresh, location.pathname])
  useEffect(() => {
    const t = setInterval(refresh, POLL_MS)
    return () => clearInterval(t)
  }, [refresh])

  return (
    <>
      {/* Overlay mobile */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={onClose}
          aria-hidden
        />
      )}

      <aside
        className={clsx(
          'w-64 bg-gray-900 flex flex-col z-40',
          // Mobile : drawer fixe coulissant ; Desktop : colonne statique
          'fixed inset-y-0 left-0 transform transition-transform duration-200 lg:static lg:translate-x-0 lg:transform-none lg:min-h-screen',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="px-6 py-5 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xs">A</span>
            </div>
            <div>
              <p className="text-white font-semibold text-sm">Alice</p>
              <p className="text-gray-400 text-xs">Admin SaaS</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white lg:hidden"
            aria-label="Fermer le menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => {
            const badge = to === '/demandes' && newLeads > 0 ? newLeads : 0
            return (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  )
                }
              >
                <Icon size={18} />
                <span className="flex-1">{label}</span>
                {badge > 0 && (
                  <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-red-500 text-white text-xs font-semibold flex items-center justify-center">
                    {badge > 99 ? '99+' : badge}
                  </span>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-gray-700">
          <p className="text-gray-500 text-xs text-center">Le Comptoir Immo SaaS</p>
        </div>
      </aside>
    </>
  )
}
