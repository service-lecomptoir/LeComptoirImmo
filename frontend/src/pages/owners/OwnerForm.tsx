import { useForm, UseFormRegister, FieldErrors } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Building2 } from 'lucide-react'
import { Modal } from '@/components/common/Modal'
import { ownersApi } from '@/api/owners'
import type { Owner, OwnerCreate } from '@/types/owner'

const schema = z.object({
  civility: z.enum(['M', 'Mme', 'Autre']).optional(),
  first_name: z.string().optional(),
  last_name: z.string().min(1, 'Nom / dénomination requis'),
  company_name: z.string().optional(),
  national_id: z.string().optional(),
  email: z.string().email('Email invalide').optional().or(z.literal('')),
  phone: z.string().optional(),
  phone2: z.string().optional(),
  address: z.string().optional(),
  iban: z.string().optional(),
  bic: z.string().optional(),
  bank_holder: z.string().optional(),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

// Champ module-level (évite la perte de focus au re-render)
interface FieldProps {
  label: string
  name: keyof FormData
  type?: string
  required?: boolean
  placeholder?: string
  register: UseFormRegister<FormData>
  errors: FieldErrors<FormData>
}
function OwnerField({ label, name, type = 'text', required = false, placeholder, register, errors }: FieldProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        {...register(name)}
        type={type}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {errors[name] && <p className="mt-1 text-xs text-red-600">{errors[name]?.message as string}</p>}
    </div>
  )
}

interface Props {
  owner?: Owner
  onClose: () => void
  onSaved: () => void
}

export function OwnerForm({ owner, onClose, onSaved }: Props) {
  const isEdit = !!owner

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: owner ? {
      civility: owner.civility ?? undefined,
      first_name: owner.first_name ?? '',
      last_name: owner.last_name,
      company_name: owner.company_name ?? '',
      national_id: owner.national_id ?? '',
      email: owner.email ?? '',
      phone: owner.phone ?? '',
      phone2: owner.phone2 ?? '',
      address: owner.address ?? '',
      iban: owner.iban ?? '',
      bic: owner.bic ?? '',
      bank_holder: owner.bank_holder ?? '',
      notes: owner.notes ?? '',
    } : {},
  })

  const onSubmit = async (data: FormData) => {
    const payload: OwnerCreate = {
      ...data,
      email: data.email || undefined,
      iban: data.iban ? data.iban.replace(/\s+/g, '').toUpperCase() : undefined,
      bic: data.bic ? data.bic.replace(/\s+/g, '').toUpperCase() : undefined,
    }
    if (isEdit) {
      await ownersApi.update(owner.id, payload)
    } else {
      await ownersApi.create(payload)
    }
    onSaved()
  }

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? 'Modifier le propriétaire' : 'Nouveau propriétaire'}
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
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700 flex items-center gap-2">
          <Building2 size={14} />
          Fiche propriétaire (bailleur). Le compte de connexion en ligne est facultatif et se crée
          depuis <span className="font-semibold">Administration</span>.
        </div>

        {/* Identité */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Identité</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Civilité</label>
              <select {...register('civility')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value=""></option>
                <option value="M">M.</option>
                <option value="Mme">Mme</option>
                <option value="Autre">Autre</option>
              </select>
            </div>
            <OwnerField label="Prénom" name="first_name" register={register} errors={errors} />
            <OwnerField label="Nom" name="last_name" required register={register} errors={errors} />
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <OwnerField label="Société / SCI (le cas échéant)" name="company_name" placeholder="SCI Les Tilleuls" register={register} errors={errors} />
            <OwnerField label="SIRET / N° pièce" name="national_id" register={register} errors={errors} />
          </div>
        </div>

        {/* Contact */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Contact</h3>
          <div className="grid grid-cols-3 gap-3">
            <OwnerField label="Email" name="email" type="email" register={register} errors={errors} />
            <OwnerField label="Téléphone" name="phone" register={register} errors={errors} />
            <OwnerField label="Téléphone 2" name="phone2" register={register} errors={errors} />
          </div>
          <div className="mt-3">
            <OwnerField label="Adresse (chèque / espèces)" name="address" placeholder="12 rue de la République, 75001 Paris" register={register} errors={errors} />
          </div>
        </div>

        {/* Coordonnées bancaires */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Coordonnées bancaires (RIB)</h3>
          <p className="text-xs text-gray-400 mb-3">Communiquées au locataire pour le règlement du loyer.</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-3">
              <OwnerField label="Titulaire du compte" name="bank_holder" register={register} errors={errors} />
            </div>
            <div className="col-span-2">
              <OwnerField label="IBAN" name="iban" placeholder="FR76 3000 4028 3798 7654 3210 943" register={register} errors={errors} />
            </div>
            <OwnerField label="BIC" name="bic" placeholder="BNPAFRPPXXX" register={register} errors={errors} />
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
