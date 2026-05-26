import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Edit, Trash2,
  MapPin, Home, Ruler, BedDouble, Bath, Layers, Euro
} from 'lucide-react'
import { propertiesApi } from '@/api/properties'
import { PropertyForm } from './PropertyForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Property } from '@/types/property'
import { PROPERTY_TYPE_LABELS } from '@/types/property'

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [property, setProperty] = useState<Property | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showEditProp, setShowEditProp] = useState(false)
  const [showDeleteProp, setShowDeleteProp] = useState(false)
  const [isDeletingProp, setIsDeletingProp] = useState(false)

  const fetchData = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const propRes = await propertiesApi.get(id)
      setProperty(propRes.data)
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

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!property) return <div className="p-6 text-sm text-red-600">Bien introuvable</div>

  const totalMonthly = (property.base_rent ?? 0) + (property.charges_amount ?? 0)
  const fmt = (n: number) => n.toLocaleString('fr-FR', { minimumFractionDigits: 2 })

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
            <StatusBadge
              label={property.is_occupied ? 'Occupé' : 'Disponible'}
              variant={property.is_occupied ? 'yellow' : 'green'}
              dot
            />
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

      {/* Caractéristiques */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Caractéristiques</h2>
        <div className="grid grid-cols-3 md:grid-cols-4 gap-4">
          <Stat icon={<Ruler size={16} className="text-blue-600" />} label="Surface"
            value={property.area_sqm ? `${property.area_sqm} m²` : '—'} />
          <Stat icon={<Layers size={16} className="text-blue-600" />} label="Étage"
            value={property.floor != null ? String(property.floor) : '—'} />
          <Stat icon={<Home size={16} className="text-blue-600" />} label="Pièces"
            value={property.rooms != null ? String(property.rooms) : '—'} />
          <Stat icon={<BedDouble size={16} className="text-blue-600" />} label="Chambres"
            value={property.bedrooms != null ? String(property.bedrooms) : '—'} />
          <Stat icon={<Bath size={16} className="text-blue-600" />} label="Salles de bain"
            value={property.bathrooms != null ? String(property.bathrooms) : '—'} />
        </div>
      </div>

      {/* Loyer & charges */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center">
            <Euro size={18} className="text-green-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{fmt(property.base_rent ?? 0)} €</p>
            <p className="text-xs text-gray-500">Loyer hors charges</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
            <Euro size={18} className="text-blue-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{fmt(property.charges_amount ?? 0)} €</p>
            <p className="text-xs text-gray-500">Charges</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-50 rounded-xl flex items-center justify-center">
            <Euro size={18} className="text-purple-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{fmt(totalMonthly)} €</p>
            <p className="text-xs text-gray-500">Total mensuel</p>
          </div>
        </div>
      </div>

      {/* Propriétaire */}
      {(property.owner_name || property.owner_email || property.owner_phone) && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
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

      {/* Notes */}
      {property.notes && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-2">Notes</h2>
          <p className="text-sm text-gray-600 whitespace-pre-line">{property.notes}</p>
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
      <ConfirmDialog
        isOpen={showDeleteProp}
        onClose={() => setShowDeleteProp(false)}
        onConfirm={handleDeleteProperty}
        title="Supprimer le bien"
        message="Cette action supprimera définitivement ce bien. Êtes-vous sûr ?"
        isLoading={isDeletingProp}
      />
    </div>
  )
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-9 h-9 bg-gray-50 rounded-lg flex items-center justify-center">{icon}</div>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm font-medium text-gray-900">{value}</p>
      </div>
    </div>
  )
}
