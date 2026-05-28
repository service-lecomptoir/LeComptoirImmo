import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Building2, Pencil, Trash2 } from 'lucide-react'
import { propertiesApi } from '@/api/properties'
import { PropertyForm } from './PropertyForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Property, PropertyListItem } from '@/types/property'

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  maison: 'Maison',
  appartement: 'Appartement',
  local_commercial: 'Local commercial',
  autre: 'Autre',
}

const TYPE_VARIANT: Record<string, 'blue' | 'green' | 'yellow' | 'gray'> = {
  maison: 'green',
  appartement: 'blue',
  local_commercial: 'yellow',
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
      fetchProperties(search)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Propriétés</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} bien{total > 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => { setEditProperty(null); setShowForm(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} /> Nouveau bien
        </button>
      </div>

      {/* Search */}
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

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-sm text-gray-400">Chargement...</div>
        ) : properties.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-400">
            <Building2 size={36} className="text-gray-300 mb-3" />
            <p className="text-sm font-medium">{search ? 'Aucun résultat' : 'Aucun bien enregistré'}</p>
            {!search && <p className="text-xs mt-1">Cliquez sur « Nouveau bien » pour commencer</p>}
          </div>
        ) : (
          <table className="w-full text-sm">
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
              {properties.map(prop => (
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
                  <td className="px-4 py-3">
                    <span className="font-medium text-gray-900">{prop.name}</span>
                  </td>
                  <td className="px-4 py-3">
                    {prop.owner_name ? <span className="text-gray-700 text-xs">{prop.owner_name}</span> : null}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      prop.is_occupied
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-green-100 text-green-700'
                    }`}>
                      {prop.is_occupied ? 'Occupé' : 'Disponible'}
                    </span>
                  </td>
                  <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      {showForm && (
        <PropertyForm
          property={editProperty ?? undefined}
          onClose={() => { setShowForm(false); setEditProperty(null) }}
          onSaved={() => { setShowForm(false); setEditProperty(null); fetchProperties(search) }}
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
    </div>
  )
}
