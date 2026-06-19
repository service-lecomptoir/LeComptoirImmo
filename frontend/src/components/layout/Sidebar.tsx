import { NavLink } from 'react-router-dom'
import { MapPin, Hash, User, Building2, Home } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useFeaturesStore } from '@/store/featuresStore'
import { featureForPath, isFeatureAllowed } from '@/lib/features'
import { navForRole, proprioSectionForPath, type NavItem } from '@/lib/navigation'
import { LogoMark } from '@/components/common/Logo'
import { getDayMoment, formatLongDate } from '@/lib/dayMoment'
import { leasesApi } from '@/api/leases'
import { propertiesApi } from '@/api/properties'
import type { Role } from '@/types/auth'
import clsx from 'clsx'
import { useState, useEffect, useMemo } from 'react'

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

// ── Carte d'en-tête unifiée (emblème navy + icône orange) ────────────────────
// Utilisée pour TOUS les rôles (gestionnaire, locataire, propriétaire) afin que
// l'avatar en haut de sidebar soit identique partout. L'icône et le libellé de
// rôle s'adaptent ; `personName` ajoute une ligne « personne » (ex. locataire).
function SidebarHeaderCard({
  Icon = Building2, roleLabel, name, personName, address, refCode,
}: {
  Icon?: LucideIcon
  roleLabel: string
  name: string
  personName?: string
  address?: string
  refCode?: string | null
}) {
  // Rôle affiché sur deux lignes : 1er mot puis le qualificatif éventuel
  // (« Gestionnaire » / « mandataire »), de façon identique pour tous.
  const _parts = roleLabel.trim().split(/\s+/)
  const roleFirst = _parts[0]
  const roleRest = _parts.slice(1).join(' ')
  return (
    <div className="px-4 py-4 border-b border-gray-700">
      <div className="rounded-xl p-3.5 flex items-center gap-3 bg-brand-navy">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border border-brand-orange/70"
          style={{ background: 'rgba(255,255,255,0.14)' }}>
          <Icon size={20} className="text-brand-orange" />
        </div>
        <div className="min-w-0">
          {name && <p className="text-white font-bold text-sm leading-tight truncate">{name}</p>}
          <span className="inline-block mt-1 text-white/90 text-[9px] font-semibold uppercase tracking-wide rounded-lg px-2 py-1 text-center leading-tight"
            style={{ background: 'rgba(255,255,255,0.22)' }}>
            {roleFirst}{roleRest && <><br />{roleRest}</>}
          </span>
        </div>
      </div>
      {address && (
        <div className="flex items-start gap-1.5 mt-2 px-0.5">
          <MapPin size={11} className="text-gray-400 mt-0.5 shrink-0" />
          <p className="text-gray-400 text-xs leading-snug line-clamp-2 whitespace-pre-line">{address}</p>
        </div>
      )}
      {personName && (
        <div className="flex items-center gap-1.5 mt-1.5 px-0.5">
          <User size={10} className="text-gray-500 shrink-0" />
          <p className="text-gray-300 text-xs font-medium truncate">{personName}</p>
        </div>
      )}
      {refCode && (
        <div className="flex items-center gap-1.5 mt-1.5 px-0.5">
          <Hash size={10} className="text-gray-500 shrink-0" />
          <p className="text-gray-500 text-xs font-mono tracking-wide">{refCode}</p>
        </div>
      )}
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
  // Adresse de l'agence sur deux lignes (rue / CP ville), construite à partir des
  // champs structurés — jamais une chaîne « rue, CP ville » à virgule (convention projet).
  // Compat : un compte ancien peut avoir tout dans `address` (CP/ville absents) ; dans
  // ce cas on transforme la virgule en saut de ligne pour conserver le rendu deux lignes.
  const agencyAddress = (() => {
    if (!isGestionnaire) return ''
    const cityLine = [user?.zip_code, user?.city].filter(Boolean).join(' ')
    let street = (user?.address ?? '').trim()
    if (street) {
      // Compat : la rue contient parfois aussi « , CP Ville » (ancien format combiné).
      // On tronque la rue avant le CP (ou la ville) pour éviter le doublon avec cityLine.
      if (user?.zip_code && street.includes(user.zip_code)) {
        street = street.slice(0, street.indexOf(user.zip_code)).replace(/[,\s]+$/, '')
      } else if (user?.city && street.includes(user.city)) {
        street = street.slice(0, street.indexOf(user.city)).replace(/[,\s]+$/, '')
      } else if (!cityLine && street.includes(',')) {
        // Tout est dans `address`, CP/ville absents : virgule → saut de ligne.
        return street.replace(/,\s*/g, '\n')
      }
    }
    return [
      street,
      cityLine,
      user?.country && user.country.toLowerCase() !== 'france' ? user.country : '',
    ].filter(Boolean).join('\n')
  })()

  // Fonctionnalités autorisées par le plan (gestionnaire/GP uniquement).
  const features = useFeaturesStore(s => s.features)
  const loadFeatures = useFeaturesStore(s => s.loadFeatures)
  useEffect(() => {
    if (isGestionnaire) loadFeatures()
  }, [isGestionnaire, loadFeatures])

  // Liste de navigation : filtrée par rôle puis par plan, séparateurs orphelins
  // retirés. Mémoïsée — ne se recalcule que si le rôle ou les features changent
  // (et non à chaque rendu, ex. ouverture/fermeture du menu mobile).
  const filteredItems = useMemo<NavItem[]>(() => {
    const items = user ? navForRole(user.role) : []
    const roleFiltered = items.filter(
      (item) => !item.roles || item.roles.includes(user?.role as Role)
    )
    // Propriétaire : visibilité réglée par le gestionnaire (rubriques autorisées).
    const sections = user?.proprio_sections
    const visFiltered = (user?.role === 'proprietaire' && Array.isArray(sections))
      ? roleFiltered.filter((item) => {
          if (item.isSeparator) return true
          const key = proprioSectionForPath(item.to)
          return !key || sections.includes(key)
        })
      : roleFiltered
    const featureFiltered = visFiltered.filter(
      (item) => item.isSeparator || isFeatureAllowed(features, featureForPath(item.to ?? ''))
    )
    return featureFiltered.filter((item, idx) => {
      if (!item.isSeparator) return true
      const next = featureFiltered[idx + 1]
      return !!next && !next.isSeparator
    })
  }, [user, features])

  // ── Header sidebar ────────────────────────────────────────────────────────
  const renderHeader = () => {
    if (isLocataire) {
      return leaseInfo
        ? <SidebarHeaderCard
            Icon={Home}
            roleLabel="Locataire"
            name={leaseInfo.propertyName}
            personName={leaseInfo.tenantName}
            address={leaseInfo.propertyAddress}
            refCode={user?.ref_code || leaseInfo.leaseRef}
          />
        : <div className="px-4 py-4 border-b border-gray-700"><SidebarSkeleton /></div>
    }

    if (isProprietaire) {
      return proprietaireInfo
        ? <SidebarHeaderCard
            Icon={Building2}
            roleLabel="Propriétaire"
            name={proprietaireInfo.fullName}
            address={proprietaireInfo.propertyAddress}
            refCode={user?.ref_code || proprietaireInfo.contractRef}
          />
        : <div className="px-4 py-4 border-b border-gray-700"><SidebarSkeleton /></div>
    }

    // Gestionnaire propriétaire
    if (user?.role === 'gestionnaire_proprio') {
      return (
        <SidebarHeaderCard
          roleLabel="Gestionnaire propriétaire"
          name={user.full_name ?? ''}
          address={agencyAddress}
          refCode={user.ref_code}
        />
      )
    }

    // Gestionnaire mandataire
    if (user?.role === 'gestionnaire') {
      return (
        <SidebarHeaderCard
          roleLabel="Gestionnaire mandataire"
          name={user.full_name ?? ''}
          address={agencyAddress}
          refCode={user.ref_code}
        />
      )
    }

    // Admin : logo habituel
    return (
      <div className="px-6 py-5 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <LogoMark size={20} className="text-white" />
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
                    ? 'bg-brand-navy text-white'
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

      {/* ── Pied : moment de la journée + date (visible sur toutes les pages) ── */}
      {(() => {
        const moment = getDayMoment()
        const { Icon } = moment
        return (
          <div className="px-4 py-3 border-t border-gray-700 flex items-center gap-2.5 shrink-0">
            <span className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
              style={{ background: moment.bg }}>
              <Icon size={18} style={{ color: moment.color }} />
            </span>
            <div className="min-w-0">
              <p className="text-gray-300 text-xs font-medium leading-tight">{moment.label}</p>
              <p className="text-gray-500 text-xs capitalize truncate">{formatLongDate()}</p>
            </div>
          </div>
        )
      })()}
      </aside>
    </>
  )
}
