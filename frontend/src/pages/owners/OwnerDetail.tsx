import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Edit, Trash2, Building2, Landmark, ShieldCheck } from 'lucide-react'
import { ownersApi } from '@/api/owners'
import { propertiesApi } from '@/api/properties'
import { OwnerForm } from './OwnerForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { Owner } from '@/types/owner'
import type { PropertyListItem } from '@/types/property'

const CIVILITY_LABELS: Record<string, string> = { M: 'M.', Mme: 'Mme', Autre: 'Autre' }

export default function OwnerDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [owner, setOwner] = useState<Owner | null>(null)
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

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

  useEffect(() => {
    if (!id) return
    propertiesApi.list({ limit: 500 })
      .then(r => setProperties((r.data.items ?? []).filter(p => p.owner_id === id)))
      .catch(() => {})
  }, [id])

  const handleDelete = async () => {
    if (!id) return
    setIsDeleting(true)
    try {
      await ownersApi.delete(id)
      navigate('/owners')
    } finally {
      setIsDeleting(false)
    }
  }

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!owner) return <div className="p-6 text-sm text-red-600">Propriétaire introuvable</div>

  // Tous les champs affichés ; vide → « Non renseigné » (jamais un tiret — convention projet).
  const Field = ({ label, value, mono }: { label: string; value: string | null | undefined; mono?: boolean }) => (
    <div className="min-w-0">
      <p className="text-xs text-gray-500">{label}</p>
      {value
        ? <p className={`text-sm text-gray-900 break-words ${mono ? 'font-mono' : ''}`}>{value}</p>
        : <p className="text-sm text-gray-300 italic">Non renseigné</p>}
    </div>
  )

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
        <div className="flex gap-2">
          <button
            onClick={() => setShowEdit(true)}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <Edit size={15} /> Modifier
          </button>
          <button
            onClick={() => setShowDelete(true)}
            className="flex items-center gap-2 px-3 py-2 border border-red-300 text-sm text-red-600 rounded-lg hover:bg-red-50"
          >
            <Trash2 size={15} /> Supprimer
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Identité */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Identité</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Civilité" value={owner.civility ? CIVILITY_LABELS[owner.civility] : null} />
            <Field label="Société / SCI" value={owner.company_name} />
            <Field label="Prénom" value={owner.first_name} />
            <Field label="Nom" value={owner.last_name} />
            <Field label="SIRET / N° pièce" value={owner.national_id} />
          </div>
        </div>

        {/* Contact */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Contact</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Email" value={owner.email} />
            <Field label="Téléphone" value={owner.phone} />
            <Field label="Téléphone 2" value={owner.phone2} />
            <Field label="Adresse" value={owner.address} />
          </div>
        </div>

        {/* Coordonnées bancaires */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Landmark size={15} className="text-blue-600" />
            <h2 className="text-sm font-semibold text-gray-900">Coordonnées bancaires (RIB)</h2>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <Field label="Titulaire du compte" value={owner.bank_holder} />
            <Field label="IBAN" value={owner.iban} mono />
            <Field label="BIC" value={owner.bic} mono />
          </div>
        </div>

        {/* Biens rattachés */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">
            Biens rattachés {properties.length > 0 && <span className="text-gray-400 font-normal">({properties.length})</span>}
          </h2>
          {properties.length === 0 ? (
            <p className="text-sm text-gray-300 italic">Aucun bien rattaché</p>
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
        <div className="bg-white rounded-xl border border-gray-200 p-5 md:col-span-2">
          <h2 className="text-sm font-semibold text-gray-900 mb-2">Notes</h2>
          {owner.notes
            ? <p className="text-sm text-gray-700 whitespace-pre-wrap">{owner.notes}</p>
            : <p className="text-sm text-gray-300 italic">Non renseigné</p>}
        </div>
      </div>

      {showEdit && (
        <OwnerForm
          owner={owner}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); fetchOwner() }}
        />
      )}
      <ConfirmDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Supprimer le propriétaire"
        message="Cette action est irréversible. Êtes-vous sûr de vouloir supprimer ce propriétaire ?"
        isLoading={isDeleting}
      />
    </div>
  )
}
