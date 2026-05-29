import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, Building2, FileText,
  CreditCard, Settings, Calendar,
  Home, Receipt, BookUser, Zap, PenSquare, BarChart3,
  Calculator, MessageSquare, Wrench, Wallet, FileCheck,
  MapPin, Hash, User, ShoppingBag, Package, KeyRound, TrendingUp,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { leasesApi } from '@/api/leases'
import { propertiesApi } from '@/api/properties'
import type { Role } from '@/types/auth'
import clsx from 'clsx'
import { useState, useEffect } from 'react'

interface NavItem {
  to?: string
  icon?: React.ElementType
  label: string
  roles?: Role[]
  isSeparator?: boolean
}

// Navigation Gestionnaire mandataire / Admin
const navGestionnaire: NavItem[] = [
  { label: 'Gestion locative', isSeparator: true },
  { to: '/dashboard', icon: BarChart3, label: 'Tableau de bord' },
  { to: '/owners', icon: KeyRound, label: 'Propriétaires' },
  { to: '/properties', icon: Building2, label: 'Propriétés' },
  { to: '/tenants', icon: Users, label: 'Locataires' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/quittances', icon: FileCheck, label: 'Quittances de loyer' },
  { to: '/actualisation', icon: TrendingUp, label: 'Actualisation loyers et charges' },
  { to: '/automatisation', icon: Zap, label: 'Automatisation' },
  { to: '/templates', icon: PenSquare, label: 'Templates docs' },
  { to: '/incidents', icon: MessageSquare, label: 'Messages et Incidents' },
  { to: '/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/contacts', icon: BookUser, label: "Carnet d'adresses" },
  { to: '/offres', icon: ShoppingBag, label: 'Offres & Services' },
  { to: '/admin', icon: Settings, label: 'Administration' },
  { label: 'Finances', isSeparator: true },
  { to: '/finances/revenus', icon: Wallet, label: 'Revenus' },
  { to: '/finances/biens', icon: BarChart3, label: 'Performance biens' },
  { to: '/finances/fiscal', icon: Calculator, label: 'Liasse fiscale' },
  { label: 'Mon compte', isSeparator: true },
  { to: '/abonnement', icon: Package, label: 'Mon abonnement' },
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
]

// Navigation Gestionnaire-Propriétaire : identique au mandataire SANS « Vue propriétaire »
const navGestionnairePropio: NavItem[] = [
  { label: 'Gestion locative', isSeparator: true },
  { to: '/dashboard', icon: BarChart3, label: 'Tableau de bord' },
  { to: '/properties', icon: Building2, label: 'Propriétés' },
  { to: '/tenants', icon: Users, label: 'Locataires' },
  { to: '/leases', icon: FileText, label: 'Contrats' },
  { to: '/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/payments', icon: CreditCard, label: 'Paiements' },
  { to: '/quittances', icon: FileCheck, label: 'Quittances de loyer' },
  { to: '/actualisation', icon: TrendingUp, label: 'Actualisation loyers et charges' },
  { to: '/automatisation', icon: Zap, label: 'Automatisation' },
  { to: '/templates', icon: PenSquare, label: 'Templates docs' },
  { to: '/incidents', icon: MessageSquare, label: 'Messages et Incidents' },
  { to: '/entretiens', icon: Wrench, label: 'Entretiens' },
  { to: '/contacts', icon: BookUser, label: "Carnet d'adresses" },
  { to: '/offres', icon: ShoppingBag, label: 'Offres & Services' },
  { to: '/admin', icon: Settings, label: 'Administration' },
  { label: 'Mes finances', isSeparator: true },
  { to: '/proprietaire/revenus', icon: CreditCard, label: 'Mes revenus' },
  { to: '/proprietaire/biens', icon: Building2, label: 'Performance biens' },
  { to: '/proprietaire/fiscal', icon: Calculator, label: 'Liasse fiscale' },
  { label: 'Mon compte', isSeparator: true },
  { to: '/abonnement', icon: Package, label: 'Mon abonnement' },
]

// Navigation Locataire
const navLocataire: NavItem[] = [
  { to: '/locataire', icon: Home, label: 'Mon espace' },
  { to: '/locataire/avis-echeances', icon: Calendar, label: "Avis d'échéances" },
  { to: '/locataire/payer', icon: Wallet, label: 'Payer mon loyer' },
  { to: '/locataire/paiements', icon: CreditCard, label: 'Mes paiements' },
  { to: '/locataire/messages', icon: MessageSquare, label: 'Mes messages' },
  { to: '/locataire/documents', icon: Receipt, label: 'Mes documents' },
  { to: '/locataire/offres', icon: ShoppingBag, label: 'Offres & Services' },
]

// ── Skeleton commun ───────────────────────────────────────────────────────────

function SidebarSkeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="h-3.5 bg-gray-700 rounded w-3/4" />
      <div className="h-3 bg-gray-700 rounded w-full" />
      <div className="h-3 bg-gray-700 rounded w-2/3" />
      <div className="h-2.5 bg-gray-700 rounded w-1/2 mt-1" />
    </div>
  )
}

// ── Hook : infos bail locataire ───────────────────────────────────────────────

interface LeaseInfo {
  propertyName: string
  propertyAddress: string
  tenantName: string
  leaseRef: string
}

function useLocataireLeaseInfo(active: boolean): LeaseInfo | null {
  const [info, setInfo] = useState<LeaseInfo | null>(null)

  useEffect(() => {
    if (!active) return
    const load = async () => {
      try {
        const res = await leasesApi.list({ is_active: true, limit: 1 })
        const items = (res.data as any).items ?? res.data
        const lease = items?.[0]
        if (!lease) return

        let fullAddress = ''
        try {
          const detail = await leasesApi.get(lease.id)
          fullAddress = detail.data?.parent_property?.full_address ?? ''
        } catch { /* silently ignore */ }

        setInfo({
          propertyName: lease.property_name ?? '',
          propertyAddress: fullAddress,
          tenantName: lease.tenant_full_name ?? '',
          leaseRef: String(lease.id).slice(0, 8).toUpperCase(),
        })
      } catch { /* silently ignore */ }
    }
    load()
  }, [active])

  return info
}

// ── Hook : infos propriétaire ─────────────────────────────────────────────────

interface ProprietaireInfo {
  fullName: string
  propertyAddress: string
  contractRef: string
}

function useProprietaireInfo(active: boolean, userName: string): ProprietaireInfo | null {
  const [info, setInfo] = useState<ProprietaireInfo | null>(null)

  useEffect(() => {
    if (!active) return
    const load = async () => {
      try {
        const res = await propertiesApi.list({ limit: 1 })
        const items = (res.data as any).items ?? res.data
        const prop = items?.[0]

        setInfo({
          fullName: userName,
          propertyAddress: prop?.full_address ?? '',
          contractRef: prop?.reference
            ? String(prop.reference).toUpperCase()
            : String(prop?.id ?? '').slice(0, 8).toUpperCase(),
        })
      } catch { /* silently ignore */ }
    }
    load()
  }, [active, userName])

  return info
}

// ── Bloc d'info affiché en haut de sidebar ────────────────────────────────────

interface SidebarInfoBlockProps {
  line1: string           // gras, blanc — titre principal
  address: string         // avec icône MapPin
  personName?: string     // optionnel — nom personne sous séparateur (icône User)
  refCode: string         // référence avec icône #
}

function SidebarInfoBlock({ line1, address, personName, refCode }: SidebarInfoBlockProps) {
  return (
    <div className="space-y-1.5">
      <p className="text-white font-semibold text-sm leading-tight truncate">{line1}</p>

      {address && (
        <div className="flex items-start gap-1.5">
          <MapPin size={11} className="text-gray-400 mt-0.5 shrink-0" />
          <p className="text-gray-400 text-xs leading-snug line-clamp-2">{address}</p>
        </div>
      )}

      <div className="border-t border-gray-700/60 pt-1.5 mt-1.5 space-y-1">
        {personName && (
          <div className="flex items-center gap-1.5">
            <User size={10} className="text-gray-500 shrink-0" />
            <p className="text-gray-300 text-xs font-medium truncate">{personName}</p>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <Hash size={10} className="text-gray-500 shrink-0" />
          <p className="text-gray-500 text-xs font-mono tracking-wide">{refCode}</p>
        </div>
      </div>
    </div>
  )
}

// ── Composant Sidebar ─────────────────────────────────────────────────────────

interface SidebarProps {
  mobileOpen?: boolean
  onClose?: () => void
}

export function Sidebar({ mobileOpen = false, onClose }: SidebarProps) {
  const { user } = useAuthStore()
  const isLocataire = user?.role === 'locataire'
  const isProprietaire = user?.role === 'proprietaire'

  const isGestionnaire = user?.role === 'gestionnaire' || user?.role === 'gestionnaire_proprio'
  const leaseInfo = useLocataireLeaseInfo(isLocataire)
  const proprietaireInfo = useProprietaireInfo(isProprietaire, user?.full_name ?? '')
  const agencyAddress = isGestionnaire ? (user?.address ?? '') : ''

  const getNavItems = (): NavItem[] => {
    if (!user) return []
    if (user.role === 'locataire') return navLocataire
    if (user.role === 'proprietaire') return navProprietaire
    if (user.role === 'gestionnaire_proprio') return navGestionnairePropio
    return navGestionnaire
  }

  const filteredItems = getNavItems().filter(
    (item) => !item.roles || item.roles.includes(user?.role as Role)
  )

  // ── Header sidebar ────────────────────────────────────────────────────────
  const renderHeader = () => {
    if (isLocataire) {
      return (
        <div className="px-4 py-4 border-b border-gray-700">
          {leaseInfo
            ? <SidebarInfoBlock
                line1={leaseInfo.propertyName}
                address={leaseInfo.propertyAddress}
                personName={leaseInfo.tenantName}
                refCode={leaseInfo.leaseRef}
              />
            : <SidebarSkeleton />
          }
        </div>
      )
    }

    if (isProprietaire) {
      return (
        <div className="px-4 py-4 border-b border-gray-700">
          {proprietaireInfo
            ? <SidebarInfoBlock
                line1={proprietaireInfo.fullName}
                address={proprietaireInfo.propertyAddress}
                refCode={proprietaireInfo.contractRef}
              />
            : <SidebarSkeleton />
          }
        </div>
      )
    }

    // Gestionnaire propriétaire
    if (user?.role === 'gestionnaire_proprio') {
      return (
        <div className="px-6 py-5 border-b border-gray-700">
          <p className="text-white font-semibold text-sm">Gestionnaire propriétaire</p>
          {user.full_name && <p className="text-gray-400 text-xs mt-0.5">{user.full_name}</p>}
          {agencyAddress && (
            <div className="flex items-start gap-1.5 mt-1.5">
              <MapPin size={11} className="text-gray-500 mt-0.5 shrink-0" />
              <p className="text-gray-500 text-xs leading-snug line-clamp-2">{agencyAddress}</p>
            </div>
          )}
        </div>
      )
    }

    // Gestionnaire mandataire
    if (user?.role === 'gestionnaire') {
      return (
        <div className="px-6 py-5 border-b border-gray-700">
          <p className="text-white font-semibold text-sm">Gestionnaire mandataire</p>
          {user.full_name && <p className="text-gray-400 text-xs mt-0.5">{user.full_name}</p>}
          {agencyAddress && (
            <div className="flex items-start gap-1.5 mt-1.5">
              <MapPin size={11} className="text-gray-500 mt-0.5 shrink-0" />
              <p className="text-gray-500 text-xs leading-snug line-clamp-2">{agencyAddress}</p>
            </div>
          )}
        </div>
      )
    }

    // Admin : logo habituel
    return (
      <div className="px-6 py-5 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xs">LC</span>
          </div>
          <div>
            <p className="text-white font-semibold text-sm">Le Comptoir Immo</p>
            <p className="text-gray-400 text-xs">Gestion locative</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Voile mobile : ferme le menu au clic en dehors */}
      {mobileOpen && (
        <div
          onClick={onClose}
          aria-hidden="true"
          className="fixed inset-0 bg-black/50 z-30 md:hidden no-print"
        />
      )}

      <aside
        className={clsx(
          'w-64 bg-gray-900 flex flex-col no-print z-40',
          'fixed inset-y-0 left-0 transition-transform duration-200 ease-in-out',
          'md:static md:min-h-screen md:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {renderHeader()}

      {/* ── Navigation ── */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {filteredItems.map((item, idx) => {
          if (item.isSeparator) {
            return (
              <div key={`sep-${idx}`} className="px-3 pt-4 pb-1">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{item.label}</p>
              </div>
            )
          }
          const Icon = item.icon!
          const to = item.to!
          return (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
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
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>
      </aside>
    </>
  )
}
