import { useState } from 'react'
import { useForm, UseFormRegister, FieldErrors } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Building2 } from 'lucide-react'
import { Modal } from '@/components/common/Modal'
import { PhoneInput } from '@/components/common/PhoneInput'
import { ownersApi } from '@/api/owners'
import type { Owner } from '@/types/owner'

const schema = z.object({
  civility: z.enum(['M', 'Mme', 'Autre']).optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  company_name: z.string().optional(),
  national_id: z.string().optional(),
  email: z.string().email('Email invalide').optional().or(z.literal('')),
  phone: z.string().optional(),
  address: z.string().optional(),
  iban: z.string().optional(),
  bic: z.string().optional(),
  bank_holder: z.string().optional(),
  notes: z.string().optional(),
}).refine(
  // Identité valide = personne (prénom + nom) OU personne morale (société + SIREN).
  (d) => (!!d.first_name?.trim() && !!d.last_name?.trim())
      || (!!d.company_name?.trim() && !!d.national_id?.trim()),
  {
    message: 'Renseignez soit le prénom et le nom, soit la société et le SIREN/SIRET.',
    path: ['last_name'],
  },
)

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

function PhoneField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
      <PhoneInput value={value} onChange={onChange} />
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
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: owner ? {
      civility: owner.civility ?? undefined,
      first_name: owner.first_name ?? '',
      last_name: owner.last_name,
      company_name: owner.company_name ?? '',
      national_id: owner.national_id ?? '',
      email: owner.email ?? '',
      phone: owner.phone ?? '',
      address: owner.address ?? '',
      iban: owner.iban ?? '',
      bic: owner.bic ?? '',
      bank_holder: owner.bank_holder ?? '',
      notes: owner.notes ?? '',
    } : {},
  })

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    // Champ vidé → `null` (jamais `undefined` : axios l'omet et l'API garde l'ancienne valeur).
    const clean = (v?: string): string | null => {
      const t = (v ?? '').trim()
      return t === '' ? null : t
    }
    const payload: any = {
      civility: data.civility || null,
      first_name: clean(data.first_name),
      last_name: clean(data.last_name),
      company_name: clean(data.company_name),
      national_id: clean(data.national_id),
      email: clean(data.email),
      phone: clean(data.phone),
      address: clean(data.address),
      iban: data.iban ? data.iban.replace(/\s+/g, '').toUpperCase() : null,
      bic: data.bic ? data.bic.replace(/\s+/g, '').toUpperCase() : null,
      bank_holder: clean(data.bank_holder),
      notes: clean(data.notes),
    }
    try {
      if (isEdit) {
        await ownersApi.update(owner.id, payload)
      } else {
        await ownersApi.create(payload)
      }
      onSaved()
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setSubmitError(
        Array.isArray(detail)
          ? detail.map((d: any) => `${d.loc?.slice(-1)[0] ?? ''} : ${d.msg}`).join(' · ')
          : (detail || "Erreur lors de l'enregistrement du propriétaire.")
      )
    }
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
        {submitError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {submitError}
          </div>
        )}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700 flex items-center gap-2">
          <Building2 size={14} />
          Fiche propriétaire. Le compte de connexion en ligne est facultatif et se crée
          depuis <span className="font-semibold">Gestion des utilisateurs</span>.
        </div>

        {/* Identité */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Identité</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Civilité</label>
              <select {...register('civility')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">— Sélectionner —</option>
                <option value="M">M.</option>
                <option value="Mme">Mme</option>
                <option value="Autre">Autre</option>
              </select>
            </div>
            <OwnerField label="Prénom" name="first_name" register={register} errors={errors} />
            <OwnerField label="Nom" name="last_name" register={register} errors={errors} />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Renseignez <span className="font-medium">soit</span> le prénom et le nom (personne),
            <span className="font-medium"> soit</span> la société et le SIREN/SIRET (personne morale).
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
            <OwnerField label="Société / SCI" name="company_name" placeholder="SCI Les Tilleuls" register={register} errors={errors} />
            <OwnerField label="SIREN / SIRET" name="national_id" register={register} errors={errors} />
          </div>
        </div>

        {/* Contact */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Contact</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <OwnerField label="Email" name="email" type="email" register={register} errors={errors} />
            <PhoneField label="Téléphone" value={watch('phone') || ''} onChange={v => setValue('phone', v)} />
          </div>
          <div className="mt-3">
            <OwnerField label="Adresse (chèque / espèces)" name="address" placeholder="12 rue de la République, 75001 Paris" register={register} errors={errors} />
          </div>
        </div>

        {/* Coordonnées bancaires */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Coordonnées bancaires (RIB)</h3>
          <p className="text-xs text-gray-400 mb-3">Communiquées au locataire pour le règlement du loyer.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
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
