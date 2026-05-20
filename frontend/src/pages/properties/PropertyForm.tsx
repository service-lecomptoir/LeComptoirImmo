import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/common/Modal'
import { propertiesApi } from '@/api/properties'
import type { Property } from '@/types/property'

const schema = z.object({
  name: z.string().min(1, 'Nom requis'),
  reference: z.string().optional(),
  address: z.string().min(1, 'Adresse requise'),
  address2: z.string().optional(),
  zip_code: z.string().min(1, 'Code postal requis'),
  city: z.string().min(1, 'Ville requise'),
  country: z.string().default('France'),
  property_type: z.enum(['immeuble', 'maison', 'appartement', 'local_commercial', 'autre']),
  owner_name: z.string().optional(),
  owner_email: z.string().email().optional().or(z.literal('')),
  owner_phone: z.string().optional(),
  year_built: z.number().int().min(1800).max(2100).optional().or(z.literal('')),
  description: z.string().optional(),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface Props {
  property?: Property
  onClose: () => void
  onSaved: () => void
}

export function PropertyForm({ property, onClose, onSaved }: Props) {
  const isEdit = !!property
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: property ? {
      name: property.name,
      reference: property.reference ?? '',
      address: property.address,
      address2: property.address2 ?? '',
      zip_code: property.zip_code,
      city: property.city,
      country: property.country,
      property_type: property.property_type,
      owner_name: property.owner_name ?? '',
      owner_email: property.owner_email ?? '',
      owner_phone: property.owner_phone ?? '',
      description: property.description ?? '',
      notes: property.notes ?? '',
    } : { property_type: 'immeuble', country: 'France' },
  })

  const onSubmit = async (data: FormData) => {
    const payload = {
      ...data,
      year_built: data.year_built ? Number(data.year_built) : undefined,
      owner_email: data.owner_email || undefined,
    }
    if (isEdit) {
      await propertiesApi.update(property.id, payload)
    } else {
      await propertiesApi.create(payload)
    }
    onSaved()
  }

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? 'Modifier le bien' : 'Nouveau bien immobilier'}
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
      <form className="space-y-5">
        {/* Identification */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Identification</h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Nom du bien <span className="text-red-500">*</span></label>
              <input {...register('name')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Résidence Les Acacias" />
              {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Référence</label>
              <input {...register('reference')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div className="mt-3">
            <label className="block text-xs font-medium text-gray-700 mb-1">Type de bien <span className="text-red-500">*</span></label>
            <select {...register('property_type')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="immeuble">Immeuble</option>
              <option value="maison">Maison</option>
              <option value="appartement">Appartement</option>
              <option value="local_commercial">Local commercial</option>
              <option value="autre">Autre</option>
            </select>
          </div>
        </div>

        {/* Adresse */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Adresse</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Adresse <span className="text-red-500">*</span></label>
              <input {...register('address')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              {errors.address && <p className="mt-1 text-xs text-red-600">{errors.address.message}</p>}
            </div>
            <input {...register('address2')} placeholder="Complément d'adresse" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Code postal <span className="text-red-500">*</span></label>
                <input {...register('zip_code')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Ville <span className="text-red-500">*</span></label>
                <input {...register('city')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Pays</label>
                <input {...register('country')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
          </div>
        </div>

        {/* Propriétaire */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Propriétaire</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Nom</label>
              <input {...register('owner_name')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
              <input {...register('owner_email')} type="email" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Téléphone</label>
              <input {...register('owner_phone')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
          <textarea {...register('notes')} rows={2} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
        </div>
      </form>
    </Modal>
  )
}
