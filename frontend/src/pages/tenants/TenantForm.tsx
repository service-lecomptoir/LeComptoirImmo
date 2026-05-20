import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/common/Modal'
import { tenantsApi } from '@/api/tenants'
import type { Tenant, TenantCreate } from '@/types/tenant'

const schema = z.object({
  civility: z.enum(['M', 'Mme', 'Autre']).optional(),
  first_name: z.string().min(1, 'Prénom requis'),
  last_name: z.string().min(1, 'Nom requis'),
  email: z.string().email('Email invalide').optional().or(z.literal('')),
  phone: z.string().optional(),
  phone2: z.string().optional(),
  birth_date: z.string().optional(),
  birth_place: z.string().optional(),
  national_id: z.string().optional(),
  employer: z.string().optional(),
  employer_phone: z.string().optional(),
  monthly_income: z.number().positive().optional().or(z.literal('')),
  income_source: z.string().optional(),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface Props {
  tenant?: Tenant
  onClose: () => void
  onSaved: () => void
}

export function TenantForm({ tenant, onClose, onSaved }: Props) {
  const isEdit = !!tenant
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: tenant ? {
      civility: tenant.civility ?? undefined,
      first_name: tenant.first_name,
      last_name: tenant.last_name,
      email: tenant.email ?? '',
      phone: tenant.phone ?? '',
      phone2: tenant.phone2 ?? '',
      birth_date: tenant.birth_date ?? '',
      birth_place: tenant.birth_place ?? '',
      national_id: tenant.national_id ?? '',
      employer: tenant.employer ?? '',
      employer_phone: tenant.employer_phone ?? '',
      notes: tenant.notes ?? '',
    } : {},
  })

  const onSubmit = async (data: FormData) => {
    const payload: TenantCreate = {
      ...data,
      email: data.email || undefined,
      monthly_income: data.monthly_income ? Number(data.monthly_income) : undefined,
    }
    if (isEdit) {
      await tenantsApi.update(tenant.id, payload)
    } else {
      await tenantsApi.create(payload)
    }
    onSaved()
  }

  const Field = ({ label, name, type = 'text', required = false }: { label: string; name: keyof FormData; type?: string; required?: boolean }) => (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        {...register(name)}
        type={type}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {errors[name] && <p className="mt-1 text-xs text-red-600">{errors[name]?.message as string}</p>}
    </div>
  )

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? 'Modifier le locataire' : 'Nouveau locataire'}
      size="lg"
      footer={
        <>
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
            Annuler
          </button>
          <button
            onClick={handleSubmit(onSubmit)}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Créer'}
          </button>
        </>
      }
    >
      <form className="space-y-4">
        {/* Identité */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Identité</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Civilité</label>
              <select {...register('civility')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">—</option>
                <option value="M">M.</option>
                <option value="Mme">Mme</option>
                <option value="Autre">Autre</option>
              </select>
            </div>
            <Field label="Prénom" name="first_name" required />
            <Field label="Nom" name="last_name" required />
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <Field label="Date de naissance" name="birth_date" type="date" />
            <Field label="Lieu de naissance" name="birth_place" />
            <Field label="N° pièce d'identité" name="national_id" />
          </div>
        </div>

        {/* Contact */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Contact</h3>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Email" name="email" type="email" />
            <Field label="Téléphone" name="phone" />
            <Field label="Téléphone 2" name="phone2" />
          </div>
        </div>

        {/* Situation professionnelle */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Situation professionnelle</h3>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Employeur" name="employer" />
            <Field label="Tél. employeur" name="employer_phone" />
            <Field label="Revenu mensuel (€)" name="monthly_income" type="number" />
          </div>
          <div className="mt-3">
            <Field label="Source de revenus" name="income_source" />
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            {...register('notes')}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>
      </form>
    </Modal>
  )
}
