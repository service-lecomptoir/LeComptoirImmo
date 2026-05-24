import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Users, Building2, FileText,
  CreditCard, Bell, Settings, LogOut, Calendar,
  Home, Receipt, BookUser, Zap, PenSquare, BarChart3,
  Calculator, MessageSquare, Wrench, Wallet, FileCheck,
  MapPin, Hash,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { leasesApi } from '@/api/leases'
import type { Role } from '@/types/auth'
import clsx from 'clsx'
import { useState, useEffect } from 'react'

interface NavItem {
  to: string
  icon: React.ElementType
  label: string
  roles?: Role[]
}

// Navigation Gestionnaire / Admin
const navGestionnaire: NavItem[] = [
  { to: '/dashboard', icon: BarChart3, label: 'Tableau de bord' },
  { to: '/properties', icon: Building2, label: 'Propriétés' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/quittances', icon: FileCheck, label: 'Quittances de loyer' },
  { to: '/incidents', icon: MessageSquare, label: 'Incidents & messages' },
  { to: '/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/automatisation', icon: Zap, label: 'Automatisation' },
  { to: '/templates', icon: PenSquare, label: 'Templates docs' },
  { to: '/contacts', icon: BookUser, label: "Carnet d'adresses" },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
  { to: '/admin', icon: Settings, label: 'Administration' },
]

// Navigation Propriétaire
const navProprietaire: NavItem[] = [
  { to: '/proprietaire', icon: LayoutDashboard, label: 'Mon tableau de bord' },
  { to: '/proprietaire/biens', icon: Building2, label: 'Mes biens' },
  { to: '/proprietaire/revenus', icon: CreditCard, label: 'Mes revenus' },
  { to: '/proprietaire/locataires', icon: Users, label: 'Mes locataires' },
  { to: '/proprietaire/incidents', icon: MessageSquare, label: 'Incidents' },
  { to: '/proprietaire/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/proprietaire/messages', icon: MessageSquare, label: 'Messages' },
  { to: '/proprietaire/fiscal', icon: Calculator, label: 'Liasse fiscale' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
]

// Navigation Locataire
const navLocataire: NavItem[] = [
  { to: '/locataire', icon: Home, label: 'Mon espace' },
  { to: '/locataire/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/locataire/payer', icon: Wallet, label: 'Payer mon loyer' },
  { to: '/locataire/paiements', icon: CreditCard, label: 'Mes paiements' },
  { to: '/locataire/messages', icon: MessageSquare, label: 'Mes messages' },
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

// ── Infos bail pour le locataire ──────────────────────────────────────────────

interface LeaseInfo {
  propertyName: string
  propertyAddress: string
  tenantName: string
  leaseRef: string
}

function useLocataireLeaseInfo(isLocataire: boolean): LeaseInfo | null {
  const [info, setInfo] = useState<LeaseInfo | null>(null)

  useEffect(() => {
    if (!isLocataire) return
    const load = async () => {
      try {
        const res = await leasesApi.list({ is_active: true, limit: 1 })
        const items = (res.data as any).items ?? res.data
        const lease = items?.[0]
        if (!lease) return

        // Essayer de charger le détail pour avoir l'adresse complète
        let fullAddress = ''
        try {
          const detail = await leasesApi.get(lease.id)
          fullAddress = detail.data?.parent_property?.full_address ?? ''
        } catch {
          // fallback silencieux
        }

        setInfo({
          propertyName: lease.property_name ?? '—',
          propertyAddress: fullAddress,
          tenantName: lease.tenant_full_name ?? '—',
          leaseRef: String(lease.id).slice(0, 8).toUpperCase(),
        })
      } catch {
        // silently ignore
      }
    }
    load()
  }, [isLocataire])

  return info
}

// ── Composant Sidebar ─────────────────────────────────────────────────────────

export function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const isLocataire = user?.role === 'locataire'
  const leaseInfo = useLocataireLeaseInfo(isLocataire)

  const getNavItems = (): NavItem[] => {
    if (!user) return []
    if (user.role === 'locataire') return navLocataire
    if (user.role === 'proprietaire') return navProprietaire
    return navGestionnaire
  }

  const filteredItems = getNavItems().filter(
    (item) => !item.roles || item.roles.includes(user?.role as Role)
  )

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-64 min-h-screen bg-gray-900 flex flex-col">

      {/* ── Header sidebar ── */}
      {isLocataire ? (
        /* Locataire : infos du bien + contrat */
        <div className="px-4 py-4 border-b border-gray-700">
          {leaseInfo ? (
            <div className="space-y-1.5">
              {/* Nom du bien */}
              <p className="text-white font-semibold text-sm leading-tight truncate">
                {leaseInfo.propertyName}
              </p>

              {/* Adresse */}
              {leaseInfo.propertyAddress && (
                <div className="flex items-start gap-1.5">
                  <MapPin size={11} className="text-gray-400 mt-0.5 shrink-0" />
                  <p className="text-gray-400 text-xs leading-snug line-clamp-2">
                    {leaseInfo.propertyAddress}
                  </p>
                </div>
              )}

              {/* Séparateur */}
              <div className="border-t border-gray-700/60 pt-1.5 mt-1.5 space-y-1">
                {/* Nom locataire */}
                <p className="text-gray-300 text-xs font-medium truncate">
                  {leaseInfo.tenantName}
                </p>

                {/* Référence contrat */}
                <div className="flex items-center gap-1.5">
                  <Hash size={10} className="text-gray-500 shrink-0" />
                  <p className="text-gray-500 text-xs font-mono tracking-wide">
                    {leaseInfo.leaseRef}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            /* Skeleton pendant le chargement */
            <div className="space-y-2 animate-pulse">
              <div className="h-3.5 bg-gray-700 rounded w-3/4" />
              <div className="h-3 bg-gray-700 rounded w-full" />
              <div className="h-3 bg-gray-700 rounded w-2/3" />
              <div className="h-2.5 bg-gray-700 rounded w-1/2 mt-1" />
            </div>
          )}
        </div>
      ) : (
        /* Gestionnaire / Propriétaire : logo habituel */
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
      )}

      {/* ── Navigation ── */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
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

      {/* ── Pied de sidebar : uniquement pour gestionnaire/propriétaire ── */}
      {!isLocataire && (
        <div className="px-3 py-4 border-t border-gray-700">
          <div className="px-3 py-2 mb-2">
            <p className="text-white text-sm font-medium truncate">{user?.full_name}</p>
            <p className="text-gray-400 text-xs truncate">{user?.email}</p>
            <span className="inline-block mt-1 px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded-full">
              {ROLE_LABEL[user?.role as Role] ?? user?.role}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <LogOut size={18} />
            <span>Déconnexion</span>
          </button>
        </div>
      )}
    </aside>
  )
}
