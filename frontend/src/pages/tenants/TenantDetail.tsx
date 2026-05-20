import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Edit, Mail, Phone, Calendar, Briefcase, StickyNote } from 'lucide-react'
import { tenantsApi } from '@/api/tenants'
import { TenantForm } from './TenantForm'
import type { Tenant } from '@/types/tenant'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

export default function TenantDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showEdit, setShowEdit] = useState(false)

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

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Chargement...</div>
  if (!tenant) return <div className="p-6 text-sm text-red-600">Locataire introuvable</div>

  const InfoRow = ({ icon: Icon, label, value }: { icon: any; label: string; value: string | null | undefined }) =>
    value ? (
      <div className="flex items-start gap-3 py-2">
        <Icon size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className="text-sm text-gray-900">{value}</p>
        </div>
      </div>
    ) : null

  return (
    <div className="p-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/tenants')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{tenant.full_name}</h1>
          <p className="text-sm text-gray-500">Fiche locataire</p>
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
            <InfoRow icon={Calendar} label="Date de naissance"
              value={tenant.birth_date ? format(new Date(tenant.birth_date), 'd MMMM yyyy', { locale: fr }) : null} />
            <InfoRow icon={Calendar} label="Lieu de naissance" value={tenant.birth_place} />
            <InfoRow icon={StickyNote} label="Pièce d'identité" value={tenant.national_id} />
          </div>
        </div>

        {/* Contact */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Contact</h2>
          <div className="divide-y divide-gray-50">
            <InfoRow icon={Mail} label="Email" value={tenant.email} />
            <InfoRow icon={Phone} label="Téléphone" value={tenant.phone} />
            <InfoRow icon={Phone} label="Téléphone 2" value={tenant.phone2} />
          </div>
        </div>

        {/* Situation professionnelle */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Situation professionnelle</h2>
          <div className="divide-y divide-gray-50">
            <InfoRow icon={Briefcase} label="Employeur" value={tenant.employer} />
            <InfoRow icon={Phone} label="Tél. employeur" value={tenant.employer_phone} />
            <InfoRow icon={StickyNote} label="Revenus mensuels"
              value={tenant.monthly_income ? `${tenant.monthly_income.toLocaleString('fr-FR')} €` : null} />
            <InfoRow icon={StickyNote} label="Source de revenus" value={tenant.income_source} />
          </div>
        </div>

        {/* Notes */}
        {tenant.notes && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Notes</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{tenant.notes}</p>
          </div>
        )}
      </div>

      {showEdit && (
        <TenantForm
          tenant={tenant}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); fetchTenant() }}
        />
      )}
    </div>
  )
}
