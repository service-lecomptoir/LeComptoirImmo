import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Edit, Mail, Phone, MapPin, Building2, Landmark,
  StickyNote, ShieldCheck, Hash,
} from 'lucide-react'
import { ownersApi } from '@/api/owners'
import { propertiesApi } from '@/api/properties'
import { OwnerForm } from './OwnerForm'
import type { Owner } from '@/types/owner'
import type { PropertyListItem } from '@/types/property'

export default function OwnerDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [owner, setOwner] = useState<Owner | null>(null)
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showEdit, setShowEdit] = useState(false)

  const fetchOwner = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const { data } = await ownersApi.get(id)
      setOwner(data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchOwner() }, [id])

  // Biens rattachés à ce propriétaire
  useEffect(() => {
    if (!id) return
    propertiesApi.list({ limit: 500 })
      .then(r => setProperties((r.data.items ?? []).filter(p => p.owner_id === id)))
      .catch(() => {})
  }, [id])

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!owner) return <div className="p-6 text-sm text-red-600">Propriétaire introuvable</div>

  const InfoRow = ({ icon: Icon, label, value, mono }: { icon: any; label: string; value: string | null | undefined; mono?: boolean }) =>
    value ? (
      <div className="flex items-start gap-3 py-2">
        <Icon size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className={`text-sm text-gray-900 ${mono ? 'font-mono' : ''}`}>{value}</p>
        </div>
      </div>
    ) : null

  const hasRib = owner.iban || owner.bic || owner.bank_holder

  return (
    <div className="p-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/owners')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">{owner.full_name}</h1>
            {owner.user_id && (
              <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full" title="Compte propriétaire lié">
                <ShieldCheck size={11} /> Compte en ligne
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500">Fiche propriétaire</p>
        </div>
        <button
          onClick={() => setShowEdit(true)}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50"
        >
          <Edit size={15} /> Modifier
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Identité */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Identité</h2>
          <div className="divide-y divide-gray-50">
            <InfoRow icon={Building2} label="Société / SCI" value={owner.company_name} />
            <InfoRow icon={Hash} label="SIRET / N° pièce" value={owner.national_id} />
          </div>
          {!owner.company_name && !owner.national_id && (
            <p className="text-sm text-gray-400">Personne physique</p>
          )}
        </div>

        {/* Contact */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Contact</h2>
          <div className="divide-y divide-gray-50">
            <InfoRow icon={Mail} label="Email" value={owner.email} />
            <InfoRow icon={Phone} label="Téléphone" value={owner.phone} />
            <InfoRow icon={Phone} label="Téléphone 2" value={owner.phone2} />
            <InfoRow icon={MapPin} label="Adresse" value={owner.address} />
          </div>
        </div>

        {/* Coordonnées bancaires */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Landmark size={15} className="text-blue-600" />
            <h2 className="text-sm font-semibold text-gray-900">Coordonnées bancaires (RIB)</h2>
          </div>
          {hasRib ? (
            <div className="divide-y divide-gray-50">
              <InfoRow icon={Landmark} label="Titulaire" value={owner.bank_holder} />
              <InfoRow icon={Landmark} label="IBAN" value={owner.iban} mono />
              <InfoRow icon={Landmark} label="BIC" value={owner.bic} mono />
            </div>
          ) : (
            <p className="text-sm text-gray-400">Aucun RIB renseigné</p>
          )}
        </div>

        {/* Biens rattachés */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">
            Biens rattachés {properties.length > 0 && <span className="text-gray-400 font-normal">({properties.length})</span>}
          </h2>
          {properties.length === 0 ? (
            <p className="text-sm text-gray-400">Aucun bien rattaché</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {properties.map(p => (
                <li key={p.id}>
                  <button
                    onClick={() => navigate(`/properties/${p.id}`)}
                    className="w-full flex items-start gap-3 py-2 text-left hover:bg-gray-50 rounded-lg px-1 -mx-1"
                  >
                    <Building2 size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-gray-900">{p.name}</p>
                      <p className="text-xs text-gray-500">{p.full_address}</p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Notes */}
        {owner.notes && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 md:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <StickyNote size={15} className="text-gray-500" />
              <h2 className="text-sm font-semibold text-gray-900">Notes</h2>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{owner.notes}</p>
          </div>
        )}
      </div>

      {showEdit && (
        <OwnerForm
          owner={owner}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); fetchOwner() }}
        />
      )}
    </div>
  )
}
