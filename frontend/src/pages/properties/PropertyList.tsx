import { useState, useEffect, useCallback, Fragment } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Building2, Pencil, Trash2, AlertTriangle, Lock, Loader2, Download, KeyRound, ChevronRight, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui'
import { propertiesApi } from '@/api/properties'
import { subscriptionApi, type SubscriptionInfo } from '@/api/subscription'
import { PropertyForm } from './PropertyForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { StatusBadge } from '@/components/common/StatusBadge'
import { CardGridSkeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { toast } from '@/store/toast'
import { exportCsv } from '@/utils/exportCsv'
import type { Property, PropertyListItem } from '@/types/property'
import { useAuthStore } from '@/store/authStore'
import { ViewToggle } from '@/components/common/ViewToggle'
import { useViewMode } from '@/hooks/useViewMode'

/**
 * Cadenas ouvert : corps dans le sens normal, anse ouverte pivotée vers la droite.
 * (l'anse est attachée à gauche du corps et s'ouvre en arc vers le haut-droite)
 */
function OpenLockRight({ size = 16 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 9.9-1" />
    </svg>
  )
}

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  maison: 'Maison',
  appartement: 'Appartement',
  local_commercial: 'Local commercial',
  autre: 'Autre',
}

const TYPE_VARIANT: Record<string, 'blue' | 'green' | 'yellow' | 'gray' | 'purple'> = {
  maison: 'green',
  appartement: 'blue',
  local_commercial: 'purple',
  autre: 'gray',
}

export default function PropertyList() {
  const navigate = useNavigate()
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editProperty, setEditProperty] = useState<Property | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [showLimitNotice, setShowLimitNotice] = useState(false)
  const [checkingLicense, setCheckingLicense] = useState(false)
  const user = useAuthStore(s => s.user)
  // Mandataire : on regroupe les biens par propriétaire (comme les autres onglets).
  const isMandataire = user?.role === 'gestionnaire'
  const [collapsedOwners, setCollapsedOwners] = useState<Set<string>>(new Set())
  const toggleOwner = (owner: string) =>
    setCollapsedOwners(prev => {
      const next = new Set(prev)
      next.has(owner) ? next.delete(owner) : next.add(owner)
      return next
    })
  const canToggleView = ['gestionnaire', 'gestionnaire_proprio', 'proprietaire'].includes(user?.role ?? '')
  const [view, setView] = useViewMode('properties', 'grid')
  const [limit, setLimit] = useState(100)

  const fetchProperties = useCallback(async (q: string, lim: number) => {
    setIsLoading(true)
    try {
      const { data } = await propertiesApi.list({ search: q || undefined, limit: lim })
      setProperties(data.items as PropertyListItem[])
      setTotal(data.total)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Interroge la licence Alice et met l'état à jour. Renvoie l'info fraîche
  // (ou null si l'abonnement est inaccessible) pour une décision immédiate.
  const fetchSubscription = useCallback(async (): Promise<SubscriptionInfo | null> => {
    try {
      const { data } = await subscriptionApi.get()
      setSubscription(data)
      return data
    } catch {
      // Abonnement inaccessible (rôle non gestionnaire ou Alice indisponible) :
      // on laisse le backend trancher à l'enregistrement.
      setSubscription(null)
      return null
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchProperties(search, limit), 300)
    return () => clearTimeout(t)
  }, [search, limit, fetchProperties])

  useEffect(() => { fetchSubscription() }, [fetchSubscription])

  // Limite connue ET atteinte/bloquée → bouton désactivé + bandeau informatif.
  const creationBlocked = subscription != null && !subscription.can_create_property

  // Clic « Nouveau bien » : on RE-vérifie la licence en temps réel (l'état
  // chargé au montage peut être périmé), puis on ouvre le formulaire seulement
  // si la création est autorisée.
  const handleNew = async () => {
    if (checkingLicense) return
    setCheckingLicense(true)
    let info: SubscriptionInfo | null
    try {
      info = await fetchSubscription()
    } finally {
      setCheckingLicense(false)
    }
    // info === null → abonnement inaccessible : on laisse passer, le backend
    // tranchera à l'enregistrement (erreur affichée dans le formulaire).
    if (info && !info.can_create_property) {
      setShowLimitNotice(true)
      return
    }
    setEditProperty(null)
    setShowForm(true)
  }

  const limitMessage = subscription?.is_blocked
    ? (subscription.plan_name
        ? "Votre compte est suspendu. Contactez votre administrateur Le Comptoir Immo pour le réactiver."
        : "Aucune licence n'est associée à votre compte. Contactez votre administrateur Le Comptoir Immo.")
    : subscription?.property_limit != null
      ? `Votre offre est limitée à ${subscription.property_limit} bien${subscription.property_limit > 1 ? 's' : ''} (${subscription.property_count} utilisé${subscription.property_count > 1 ? 's' : ''}). Passez à une offre supérieure pour en ajouter davantage.`
      : "Vous ne pouvez plus créer de nouveaux biens avec votre offre actuelle."

  const openEdit = async (id: string) => {
    try {
      const { data } = await propertiesApi.get(id)
      setEditProperty(data)
      setShowForm(true)
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    setIsDeleting(true)
    try {
      await propertiesApi.delete(deleteId)
      setDeleteId(null)
      fetchProperties(search, limit)
      fetchSubscription()
      toast.success('Bien supprimé')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleExport = () => {
    exportCsv('biens',
      ['Nom', 'Type', 'Ville', 'Adresse', 'Propriétaire', 'Occupé', 'Lots'],
      properties.map(p => [
        p.name,
        PROPERTY_TYPE_LABELS[p.property_type] ?? p.property_type,
        p.city, (p.full_address || '').replace(/\n/g, ', '), p.owner_name,
        p.is_occupied ? 'Oui' : 'Non',
        p.unit_count,
      ]))
    toast.success(`${properties.length} bien(s) exporté(s)`)
  }

  // Carte d'un bien (vue mosaïque), réutilisée en grille simple ET groupée.
  const renderCard = (prop: PropertyListItem) => (
    <div
      key={prop.id}
      onClick={() => navigate(`/properties/${prop.id}`)}
      className="group relative flex flex-col gap-3 bg-white rounded-xl border border-gray-200 shadow-sm p-4 cursor-pointer transition-all hover:shadow-md hover:border-blue-300"
    >
      {/* Type + occupation */}
      <div className="flex items-center justify-between gap-2">
        <StatusBadge
          label={PROPERTY_TYPE_LABELS[prop.property_type] ?? prop.property_type}
          variant={TYPE_VARIANT[prop.property_type] ?? 'gray'}
        />
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
          prop.is_occupied ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
        }`}>
          {prop.is_occupied ? 'Occupé' : 'Disponible'}
        </span>
      </div>

      {/* Icône + nom + adresse */}
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
          <Building2 size={18} className="text-blue-600" />
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 truncate">{prop.name}</p>
          {(prop.full_address || prop.city) && (
            <p className="text-xs text-gray-500 whitespace-pre-line leading-tight">{prop.full_address || prop.city}</p>
          )}
        </div>
      </div>

      {/* Méta : typologie / surface / lots */}
      {(prop.typology || prop.area_sqm != null || prop.unit_count > 1) && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
          {prop.typology && <span>{prop.typology}</span>}
          {prop.area_sqm != null && <span>{prop.area_sqm} m²</span>}
          {prop.unit_count > 1 && <span>{prop.unit_count} lots</span>}
        </div>
      )}

      {/* Propriétaire (masqué pour le mandataire : déjà en en-tête de groupe) + actions */}
      <div className="mt-auto flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
        <span className="text-xs text-gray-600 truncate">
          {isMandataire ? '' : (prop.owner_name || '')}
        </span>
        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
          <button
            onClick={() => openEdit(prop.id)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 transition-colors"
            title="Modifier"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => setDeleteId(prop.id)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors"
            title="Supprimer"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  )

  // Regroupement par propriétaire (mandataire uniquement), ordre alphabétique.
  const ownerGroups: [string, PropertyListItem[]][] = (() => {
    const acc: Record<string, PropertyListItem[]> = {}
    for (const p of properties) {
      const key = p.owner_name || 'Sans propriétaire'
      ;(acc[key] ||= []).push(p)
    }
    return Object.entries(acc).sort((a, b) => a[0].localeCompare(b[0], 'fr'))
  })()

  // Ligne de tableau d'un bien (vue liste) — réutilisée à plat ou par groupe.
  const renderPropRow = (prop: PropertyListItem) => (
    <tr
      key={prop.id}
      onClick={() => navigate(`/properties/${prop.id}`)}
      className="hover:bg-gray-50 cursor-pointer transition-colors"
    >
      <td className="px-4 py-3">
        <StatusBadge
          label={PROPERTY_TYPE_LABELS[prop.property_type] ?? prop.property_type}
          variant={TYPE_VARIANT[prop.property_type] ?? 'gray'}
        />
      </td>
      <td className="px-4 py-3"><span className="font-medium text-gray-900">{prop.name}</span></td>
      <td className="px-4 py-3">
        {!isMandataire && prop.owner_name ? <span className="text-gray-700 text-xs">{prop.owner_name}</span> : null}
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
          prop.is_occupied ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
        }`}>
          {prop.is_occupied ? 'Occupé' : 'Disponible'}
        </span>
      </td>
      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-end gap-1">
          <button onClick={() => openEdit(prop.id)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 transition-colors" title="Modifier">
            <Pencil size={14} />
          </button>
          <button onClick={() => setDeleteId(prop.id)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors" title="Supprimer">
            <Trash2 size={14} />
          </button>
        </div>
      </td>
    </tr>
  )

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Propriétés</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} bien{total > 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          {canToggleView && <ViewToggle value={view} onChange={setView} />}
          <Button
            variant="secondary"
            onClick={handleExport}
            disabled={properties.length === 0}
            leftIcon={<Download size={16} />}
            className="px-3"
          >
            Exporter
          </Button>
          <button
          onClick={handleNew}
          disabled={checkingLicense}
          title={creationBlocked ? limitMessage : undefined}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-70 ${
            creationBlocked
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {/* Cadenas : ouvert si l'offre permet d'ajouter un bien, fermé sinon */}
          {checkingLicense
            ? <Loader2 size={16} className="animate-spin" />
            : creationBlocked
              ? <Lock size={16} />
              : <OpenLockRight size={16} />}
          {checkingLicense ? 'Vérification…' : 'Nouveau bien'}
          </button>
        </div>
      </div>

      {/* Bandeau limite d'offre atteinte */}
      {creationBlocked && (
        <div className="mb-4 flex items-start gap-3 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3">
          <AlertTriangle size={18} className="text-orange-500 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-orange-800">Création de biens indisponible</p>
            <p className="text-orange-700 mt-0.5">{limitMessage}</p>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => { setSearch(e.target.value); setLimit(100) }}
          placeholder="Rechercher par nom, adresse, ville..."
          className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Mosaïque */}
      {isLoading && properties.length === 0 ? (
        <CardGridSkeleton />
      ) : properties.length === 0 ? (
        <EmptyState
          icon={Building2}
          title={search ? 'Aucun résultat' : 'Aucun bien enregistré'}
          hint={!search ? 'Cliquez sur « Nouveau bien » pour commencer' : undefined}
        />
      ) : view === 'list' ? (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Nom du bien</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Propriétaire</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {isMandataire
                  ? ownerGroups.map(([owner, list]) => {
                      const open = !collapsedOwners.has(owner)
                      return (
                        <Fragment key={owner}>
                          <tr className="bg-gray-50/70 hover:bg-gray-100 cursor-pointer" onClick={() => toggleOwner(owner)}>
                            <td colSpan={5} className="px-4 py-2">
                              <div className="flex items-center gap-2">
                                {open ? <ChevronDown size={15} className="text-gray-400 shrink-0" /> : <ChevronRight size={15} className="text-gray-400 shrink-0" />}
                                <KeyRound size={14} className="text-blue-600 shrink-0" />
                                <span className="text-sm font-semibold text-gray-900">{owner}</span>
                                <span className="text-xs text-gray-400">· {list.length} bien{list.length > 1 ? 's' : ''}</span>
                              </div>
                            </td>
                          </tr>
                          {open && list.map(renderPropRow)}
                        </Fragment>
                      )
                    })
                  : properties.map(renderPropRow)}
              </tbody>
            </table>
          </div>
        </div>
      ) : isMandataire ? (
        // Mandataire : biens regroupés par propriétaire (en-tête + grille de cartes).
        <div className="space-y-6">
          {ownerGroups.map(([owner, list]) => {
            const open = !collapsedOwners.has(owner)
            return (
              <div key={owner}>
                <button onClick={() => toggleOwner(owner)} className="w-full flex items-center gap-2 mb-3 text-left">
                  {open ? <ChevronDown size={15} className="text-gray-400 shrink-0" /> : <ChevronRight size={15} className="text-gray-400 shrink-0" />}
                  <KeyRound size={15} className="text-blue-600 shrink-0" />
                  <h3 className="text-sm font-semibold text-gray-900">{owner}</h3>
                  <span className="text-xs text-gray-400">· {list.length} bien{list.length > 1 ? 's' : ''}</span>
                </button>
                {open && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {list.map(renderCard)}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {properties.map(renderCard)}
        </div>
      )}

      {!isLoading && properties.length < total && properties.length < 1000 && (
        <div className="flex justify-center mt-4">
          <Button
            variant="secondary"
            onClick={() => setLimit(l => Math.min(l + 100, 1000))}
          >
            Charger plus ({properties.length} / {total})
          </Button>
        </div>
      )}

      {/* Modals */}
      {showForm && (
        <PropertyForm
          property={editProperty ?? undefined}
          onClose={() => { setShowForm(false); setEditProperty(null) }}
          onSaved={() => { setShowForm(false); setEditProperty(null); fetchProperties(search, limit); fetchSubscription(); toast.success('Bien enregistré') }}
        />
      )}
      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Supprimer le bien"
        message="Cette action supprimera définitivement ce bien. Êtes-vous sûr ?"
        isLoading={isDeleting}
      />
      <ConfirmDialog
        isOpen={showLimitNotice}
        onClose={() => setShowLimitNotice(false)}
        onConfirm={() => navigate('/abonnement')}
        title="Limite de votre offre atteinte"
        message={limitMessage}
        confirmLabel="Voir mon abonnement"
        confirmVariant="blue"
      />
    </div>
  )
}
