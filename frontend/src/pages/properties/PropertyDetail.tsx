import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Edit, Trash2, Plus, Building2,
  MapPin, Home, DoorOpen, Layers
} from 'lucide-react'
import { propertiesApi } from '@/api/properties'
import { apiClient } from '@/api/client'
import { PropertyForm } from './PropertyForm'
import { UnitForm } from './UnitForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Property, Unit } from '@/types/property'

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  immeuble: 'Immeuble',
  maison: 'Maison',
  appartement: 'Appartement',
  local_commercial: 'Local commercial',
  autre: 'Autre',
}

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [property, setProperty] = useState<Property | null>(null)
  const [units, setUnits] = useState<Unit[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showEditProp, setShowEditProp] = useState(false)
  const [showDeleteProp, setShowDeleteProp] = useState(false)
  const [isDeletingProp, setIsDeletingProp] = useState(false)
  const [showUnitForm, setShowUnitForm] = useState(false)
  const [editingUnit, setEditingUnit] = useState<Unit | undefined>()
  const [deleteUnitId, setDeleteUnitId] = useState<string | null>(null)
  const [isDeletingUnit, setIsDeletingUnit] = useState(false)

  const fetchData = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const [propRes, unitsRes] = await Promise.all([
        propertiesApi.get(id),
        apiClient.get<Unit[]>(`/properties/${id}/units`),
      ])
      setProperty(propRes.data)
      setUnits(unitsRes.data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [id])

  const handleDeleteProperty = async () => {
    if (!id) return
    setIsDeletingProp(true)
    try {
      await propertiesApi.delete(id)
      navigate('/properties')
    } finally {
      setIsDeletingProp(false)
    }
  }

  const handleDeleteUnit = async () => {
    if (!deleteUnitId) return
    setIsDeletingUnit(true)
    try {
      await apiClient.delete(`/units/${deleteUnitId}`)
      setDeleteUnitId(null)
      fetchData()
    } finally {
      setIsDeletingUnit(false)
    }
  }

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!property) return <div className="p-6 text-sm text-red-600">Bien introuvable</div>

  const occupiedCount = units.filter(u => u.is_occupied).length

  return (
    <div className="p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/properties')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{property.name}</h1>
            <StatusBadge label={PROPERTY_TYPE_LABELS[property.property_type] ?? property.property_type} variant="blue" />
          </div>
          <div className="flex items-center gap-1 text-sm text-gray-500 mt-0.5">
            <MapPin size={13} />
            <span>{property.full_address}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowEditProp(true)}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <Edit size={15} /> Modifier
          </button>
          <button
            onClick={() => setShowDeleteProp(true)}
            className="flex items-center gap-2 px-3 py-2 border border-red-300 text-sm text-red-600 rounded-lg hover:bg-red-50"
          >
            <Trash2 size={15} /> Supprimer
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
            <Layers size={18} className="text-blue-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{units.length}</p>
            <p className="text-xs text-gray-500">Logements</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center">
            <Home size={18} className="text-green-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{occupiedCount}</p>
            <p className="text-xs text-gray-500">Occupés</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-50 rounded-xl flex items-center justify-center">
            <DoorOpen size={18} className="text-orange-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{units.length - occupiedCount}</p>
            <p className="text-xs text-gray-500">Disponibles</p>
          </div>
        </div>
      </div>

      {/* Logements */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">Logements</h2>
          <button
            onClick={() => { setEditingUnit(undefined); setShowUnitForm(true) }}
            className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700"
          >
            <Plus size={13} /> Ajouter un logement
          </button>
        </div>

        {units.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Building2 size={28} className="text-gray-300 mb-2" />
            <p className="text-sm">Aucun logement enregistré</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-5 py-3">Référence</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Type</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Surface</th>
                <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Loyer HC</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Statut</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {units.map(unit => (
                <tr key={unit.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-5 py-3 text-sm font-medium text-gray-900">{unit.unit_ref}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{unit.unit_type}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {unit.area_sqm ? `${unit.area_sqm} m²` : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-right font-medium">
                    {unit.base_rent.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      label={unit.is_occupied ? 'Occupé' : 'Disponible'}
                      variant={unit.is_occupied ? 'yellow' : 'green'}
                      dot
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-end">
                      <button
                        onClick={() => { setEditingUnit(unit); setShowUnitForm(true) }}
                        className="p-1.5 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700"
                      >
                        <Edit size={14} />
                      </button>
                      <button
                        onClick={() => setDeleteUnitId(unit.id)}
                        disabled={unit.is_occupied}
                        className="p-1.5 hover:bg-red-50 rounded text-gray-400 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title={unit.is_occupied ? 'Logement occupé, résiliez le bail d\'abord' : 'Supprimer'}
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

      {/* Propriétaire */}
      {(property.owner_name || property.owner_email || property.owner_phone) && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mt-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Propriétaire</h2>
          <div className="grid grid-cols-3 gap-4">
            {property.owner_name && (
              <div>
                <p className="text-xs text-gray-500">Nom</p>
                <p className="text-sm font-medium text-gray-900">{property.owner_name}</p>
              </div>
            )}
            {property.owner_email && (
              <div>
                <p className="text-xs text-gray-500">Email</p>
                <p className="text-sm text-gray-900">{property.owner_email}</p>
              </div>
            )}
            {property.owner_phone && (
              <div>
                <p className="text-xs text-gray-500">Téléphone</p>
                <p className="text-sm text-gray-900">{property.owner_phone}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modales */}
      {showEditProp && (
        <PropertyForm
          property={property}
          onClose={() => setShowEditProp(false)}
          onSaved={() => { setShowEditProp(false); fetchData() }}
        />
      )}
      {showUnitForm && id && (
        <UnitForm
          propertyId={id}
          unit={editingUnit}
          onClose={() => setShowUnitForm(false)}
          onSaved={() => { setShowUnitForm(false); fetchData() }}
        />
      )}
      <ConfirmDialog
        isOpen={showDeleteProp}
        onClose={() => setShowDeleteProp(false)}
        onConfirm={handleDeleteProperty}
        title="Supprimer le bien"
        message="Cette action supprimera définitivement ce bien et tous ses logements. Êtes-vous sûr ?"
        isLoading={isDeletingProp}
      />
      <ConfirmDialog
        isOpen={!!deleteUnitId}
        onClose={() => setDeleteUnitId(null)}
        onConfirm={handleDeleteUnit}
        title="Supprimer le logement"
        message="Voulez-vous vraiment supprimer ce logement ?"
        isLoading={isDeletingUnit}
      />
    </div>
  )
}
