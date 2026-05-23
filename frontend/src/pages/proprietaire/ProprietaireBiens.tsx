import { useState, useEffect } from 'react'
import { Building2, MapPin, Home, Users, TrendingUp, ChevronDown, ChevronUp, CreditCard, CalendarDays } from 'lucide-react'
import { propertiesApi } from '@/api/properties'
import { leasesApi } from '@/api/leases'
import type { PropertyListItem } from '@/types/property'
import type { LeaseListItem } from '@/types/lease'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  immeuble: 'Immeuble',
  maison: 'Maison',
  appartement: 'Appartement',
  local_commercial: 'Local commercial',
  autre: 'Autre',
}

export default function ProprietaireBiens() {
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [leases, setLeases] = useState<LeaseListItem[]>([])
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [propsRes, leasesRes] = await Promise.allSettled([
          propertiesApi.list({ limit: 100 }),
          leasesApi.list({ is_active: true, limit: 200 }),
        ])

        if (propsRes.status === 'fulfilled') {
          const items = propsRes.value.data.items ?? propsRes.value.data
          setProperties(items)
          // Ouvrir le premier bien par défaut
          if (items.length > 0) {
            setExpanded({ [items[0].id]: true })
          }
        }
        if (leasesRes.status === 'fulfilled') {
          const items = leasesRes.value.data.items ?? leasesRes.value.data
          setLeases(items)
        }
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  const toggleExpand = (id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
  }

  // Total loyers pour tous les biens
  const totalRevenu = leases.reduce((sum, l) => sum + l.rent_amount + l.charges_amount, 0)

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes biens</h1>
        <p className="text-gray-500 text-sm mt-1">Vue d'ensemble de votre patrimoine en gestion</p>
      </div>

      {/* Résumé global */}
      {!isLoading && properties.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-gray-500 mb-1">
              <Building2 size={15} />
              <span className="text-xs font-medium uppercase tracking-wide">Biens</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{properties.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-gray-500 mb-1">
              <Users size={15} />
              <span className="text-xs font-medium uppercase tracking-wide">Locataires actifs</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{leases.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-gray-500 mb-1">
              <CreditCard size={15} />
              <span className="text-xs font-medium uppercase tracking-wide">Revenus / mois</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{fmtEuro(totalRevenu)}</p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400 text-sm">
          Chargement…
        </div>
      ) : properties.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400">
          <Building2 size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Aucun bien enregistré</p>
          <p className="text-sm mt-1">Contactez votre gestionnaire pour lier vos biens à votre compte.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {properties.map((prop) => {
            const propLeases = leases.filter(l => l.property_id === prop.id)
            const isOpen = !!expanded[prop.id]
            const occupancyRate = prop.unit_count > 0
              ? Math.round((prop.occupied_count / prop.unit_count) * 100)
              : 0
            const propRevenu = propLeases.reduce((s, l) => s + l.rent_amount + l.charges_amount, 0)

            return (
              <div key={prop.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* En-tête du bien */}
                <div
                  className="flex items-center justify-between p-5 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleExpand(prop.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-11 h-11 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Building2 size={20} className="text-blue-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900">{prop.name}</h3>
                        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full capitalize">
                          {PROPERTY_TYPE_LABELS[prop.property_type] ?? prop.property_type}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                        <MapPin size={11} />
                        <span>{prop.full_address}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    {/* Stats */}
                    <div className="hidden md:flex items-center gap-5 text-sm text-gray-500">
                      <div className="flex items-center gap-1.5">
                        <Home size={14} />
                        <span>{prop.occupied_count}/{prop.unit_count} occupés</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <TrendingUp size={14} />
                        <span className={occupancyRate >= 80 ? 'text-green-600 font-medium' : occupancyRate >= 50 ? 'text-yellow-600 font-medium' : 'text-red-500 font-medium'}>
                          {occupancyRate} %
                        </span>
                      </div>
                      {propRevenu > 0 && (
                        <div className="flex items-center gap-1.5">
                          <CreditCard size={14} />
                          <span className="text-gray-700 font-medium">{fmtEuro(propRevenu)}/mois</span>
                        </div>
                      )}
                    </div>
                    {isOpen ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
                  </div>
                </div>

                {/* Détail — logements & locataires */}
                {isOpen && (
                  <div className="border-t border-gray-100">
                    {propLeases.length === 0 ? (
                      <div className="px-5 py-6 text-center text-sm text-gray-400">
                        <Users size={28} className="mx-auto mb-2 text-gray-300" />
                        {prop.unit_count === 0
                          ? 'Aucun logement enregistré pour ce bien'
                          : 'Aucun bail actif — tous les logements sont vacants'
                        }
                      </div>
                    ) : (
                      <div className="divide-y divide-gray-50">
                        {propLeases.map(lease => (
                          <div key={lease.id} className="px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 bg-teal-100 rounded-full flex items-center justify-center flex-shrink-0">
                                <span className="text-teal-700 text-xs font-bold">
                                  {lease.tenant_full_name.charAt(0).toUpperCase()}
                                </span>
                              </div>
                              <div>
                                <p className="text-sm font-medium text-gray-900">{lease.tenant_full_name}</p>
                                <div className="flex items-center gap-3 mt-0.5">
                                  <span className="text-xs text-gray-500 flex items-center gap-1">
                                    <Home size={10} /> {lease.unit_ref}
                                  </span>
                                  <span className="text-xs text-gray-400 capitalize">{lease.lease_type}</span>
                                  <span className="text-xs text-gray-400 flex items-center gap-0.5">
                                    <CalendarDays size={10} />
                                    depuis {format(new Date(lease.start_date), 'MMM yyyy', { locale: fr })}
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-semibold text-gray-900">
                                {fmtEuro(lease.rent_amount + lease.charges_amount)}
                              </p>
                              <p className="text-xs text-gray-400">/ mois</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Logements vacants */}
                    {prop.unit_count > prop.occupied_count && (
                      <div className="px-5 py-3 bg-amber-50 border-t border-amber-100 flex items-center gap-2">
                        <Home size={14} className="text-amber-500" />
                        <span className="text-xs text-amber-700">
                          {prop.unit_count - prop.occupied_count} logement{prop.unit_count - prop.occupied_count > 1 ? 's' : ''} vacant{prop.unit_count - prop.occupied_count > 1 ? 's' : ''}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
