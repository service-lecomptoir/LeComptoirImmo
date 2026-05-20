import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Building2, MapPin } from 'lucide-react'
import { propertiesApi } from '@/api/properties'
import { PropertyForm } from './PropertyForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { PropertyListItem } from '@/types/property'

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  immeuble: 'Immeuble',
  maison: 'Maison',
  appartement: 'Appartement',
  local_commercial: 'Local commercial',
  autre: 'Autre',
}

export default function PropertyList() {
  const navigate = useNavigate()
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const fetchProperties = useCallback(async (q: string) => {
    setIsLoading(true)
    try {
      const { data } = await propertiesApi.list({ search: q || undefined, limit: 100 })
      setProperties(data.items as PropertyListItem[])
      setTotal(data.total)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchProperties(search), 300)
    return () => clearTimeout(t)
  }, [search, fetchProperties])

  const handleDelete = async () => {
    if (!deleteId) return
    setIsDeleting(true)
    try {
      await propertiesApi.delete(deleteId)
      setDeleteId(null)
      fetchProperties(search)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Biens immobiliers</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} bien{total > 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} /> Nouveau bien
        </button>
      </div>

      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher par nom, adresse, ville..."
          className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-3 flex items-center justify-center h-32 text-sm text-gray-500">Chargement...</div>
        ) : properties.length === 0 ? (
          <div className="col-span-3 flex flex-col items-center justify-center h-32 text-gray-500">
            <Building2 size={32} className="text-gray-300 mb-2" />
            <p className="text-sm">{search ? 'Aucun résultat' : 'Aucun bien enregistré'}</p>
          </div>
        ) : properties.map(prop => {
          const occupancyRate = prop.unit_count > 0
            ? Math.round((prop.occupied_count / prop.unit_count) * 100)
            : 0
          return (
            <div
              key={prop.id}
              onClick={() => navigate(`/properties/${prop.id}`)}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-blue-200 cursor-pointer transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
                  <Building2 size={20} className="text-blue-600" />
                </div>
                <StatusBadge
                  label={PROPERTY_TYPE_LABELS[prop.property_type]}
                  variant="blue"
                />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">{prop.name}</h3>
              <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
                <MapPin size={11} />
                <span>{prop.full_address}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">
                  {prop.unit_count} logement{prop.unit_count > 1 ? 's' : ''}
                </span>
                <StatusBadge
                  label={`${prop.occupied_count}/${prop.unit_count} occupés`}
                  variant={occupancyRate > 80 ? 'green' : occupancyRate > 50 ? 'yellow' : 'gray'}
                  dot
                />
              </div>
            </div>
          )
        })}
      </div>

      {showForm && (
        <PropertyForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchProperties(search) }}
        />
      )}
      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Supprimer le bien"
        message="Cette action supprimera aussi tous les logements associés. Êtes-vous sûr ?"
        isLoading={isDeleting}
      />
    </div>
  )
}
