import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Edit, Trash2, ShieldCheck } from 'lucide-react'
import { tenantsApi } from '@/api/tenants'
import { TenantForm } from './TenantForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { Tenant } from '@/types/tenant'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const CIVILITY_LABELS: Record<string, string> = { M: 'M.', Mme: 'Mme', Autre: 'Autre' }

export default function TenantDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const fetchTenant = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const { data } = await tenantsApi.get(id)
      setTenant(data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { fetchTenant() }, [id])

  const handleDelete = async () => {
    if (!id) return
    setIsDeleting(true)
    try {
      await tenantsApi.delete(id)
      navigate('/tenants')
    } finally {
      setIsDeleting(false)
    }
  }

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!tenant) return <div className="p-6 text-sm text-red-600">Locataire introuvable</div>

  // Tous les champs sont affichés ; les valeurs vides sont signalées « Non renseigné »
  // (jamais un tiret — convention projet).
  const Field = ({ label, value }: { label: string; value: string | null | undefined }) => (
    <div className="min-w-0">
      <p className="text-xs text-gray-500">{label}</p>
      {value
        ? <p className="text-sm text-gray-900 break-words">{value}</p>
        : <p className="text-sm text-gray-300 italic">Non renseigné</p>}
    </div>
  )

  const birthDate = tenant.birth_date
    ? format(new Date(tenant.birth_date), 'd MMMM yyyy', { locale: fr })
    : null
  const income = tenant.monthly_income != null
    ? `${Number(tenant.monthly_income).toLocaleString('fr-FR')} €`
    : null

  return (
    <div className="p-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/tenants')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">{tenant.full_name}</h1>
            {tenant.user_id && (
              <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full" title="Compte locataire lié">
                <ShieldCheck size={11} /> Compte en ligne
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500">Fiche locataire</p>
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
            <Field label="Civilité" value={tenant.civility ? CIVILITY_LABELS[tenant.civility] : null} />
            <Field label="Prénom" value={tenant.first_name} />
            <Field label="Nom" value={tenant.last_name} />
            <Field label="Date de naissance" value={birthDate} />
            <Field label="Lieu de naissance" value={tenant.birth_place} />
            <Field label="Pièce d'identité" value={tenant.national_id} />
          </div>
        </div>

        {/* Contact */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Contact</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Email" value={tenant.email} />
            <Field label="Téléphone" value={tenant.phone} />
            <Field label="Téléphone 2" value={tenant.phone2} />
          </div>
        </div>

        {/* Situation professionnelle */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Situation professionnelle</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Employeur" value={tenant.employer} />
            <Field label="Tél. employeur" value={tenant.employer_phone} />
            <Field label="Revenu mensuel" value={income} />
            <Field label="Source de revenus" value={tenant.income_source} />
          </div>
        </div>

        {/* Notes */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Notes</h2>
          {tenant.notes
            ? <p className="text-sm text-gray-700 whitespace-pre-wrap">{tenant.notes}</p>
            : <p className="text-sm text-gray-300 italic">Non renseigné</p>}
        </div>
      </div>

      {showEdit && (
        <TenantForm
          tenant={tenant}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); fetchTenant() }}
        />
      )}
      <ConfirmDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Supprimer le locataire"
        message="Cette action est irréversible. Êtes-vous sûr de vouloir supprimer ce locataire ?"
        isLoading={isDeleting}
      />
    </div>
  )
}
