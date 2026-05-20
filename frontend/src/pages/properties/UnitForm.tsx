import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/common/Modal'
import { apiClient } from '@/api/client'
import type { Unit } from '@/types/property'

const schema = z.object({
  unit_ref: z.string().min(1, 'Référence requise'),
  unit_type: z.enum(['studio', 'T1', 'T2', 'T3', 'T4', 'T5+', 'maison', 'local', 'autre']),
  floor: z.coerce.number().int().optional().or(z.literal('')),
  building: z.string().optional(),
  area_sqm: z.coerce.number().positive().optional().or(z.literal('')),
  rooms: z.coerce.number().int().positive().optional().or(z.literal('')),
  bedrooms: z.coerce.number().int().positive().optional().or(z.literal('')),
  bathrooms: z.coerce.number().int().positive().optional().or(z.literal('')),
  base_rent: z.coerce.number().positive('Loyer requis'),
  charges_amount: z.coerce.number().min(0).default(0),
  deposit_months: z.coerce.number().int().min(0).default(1),
  is_available: z.boolean().default(true),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface Props {
  propertyId: string
  unit?: Unit
  onClose: () => void
  onSaved: () => void
}

export function UnitForm({ propertyId, unit, onClose, onSaved }: Props) {
  const isEdit = !!unit
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: unit
      ? {
          unit_ref: unit.unit_ref,
          unit_type: unit.unit_type,
          floor: unit.floor ?? '',
          building: unit.building ?? '',
          area_sqm: unit.area_sqm ?? '',
          rooms: unit.rooms ?? '',
          bedrooms: unit.bedrooms ?? '',
          bathrooms: unit.bathrooms ?? '',
          base_rent: unit.base_rent,
          charges_amount: unit.charges_amount,
          deposit_months: unit.deposit_months,
          is_available: unit.is_available,
          notes: unit.notes ?? '',
        }
      : {
          unit_type: 'T2',
          charges_amount: 0,
          deposit_months: 1,
          is_available: true,
        },
  })

  const onSubmit = async (data: FormData) => {
    const payload = {
      ...data,
      property_id: propertyId,
      floor: data.floor !== '' ? Number(data.floor) : undefined,
      area_sqm: data.area_sqm !== '' ? Number(data.area_sqm) : undefined,
      rooms: data.rooms !== '' ? Number(data.rooms) : undefined,
      bedrooms: data.bedrooms !== '' ? Number(data.bedrooms) : undefined,
      bathrooms: data.bathrooms !== '' ? Number(data.bathrooms) : undefined,
    }
    if (isEdit) {
      await apiClient.put(`/units/${unit.id}`, payload)
    } else {
      await apiClient.post('/units', payload)
    }
    onSaved()
  }

  const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const labelCls = 'block text-xs font-medium text-gray-700 mb-1'
  const errCls = 'mt-1 text-xs text-red-600'

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? 'Modifier le logement' : 'Nouveau logement'}
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
            <div>
              <label className={labelCls}>Référence <span className="text-red-500">*</span></label>
              <input {...register('unit_ref')} className={inputCls} placeholder="Apt 1A" />
              {errors.unit_ref && <p className={errCls}>{errors.unit_ref.message}</p>}
            </div>
            <div>
              <label className={labelCls}>Type <span className="text-red-500">*</span></label>
              <select {...register('unit_type')} className={inputCls}>
                <option value="studio">Studio</option>
                <option value="T1">T1</option>
                <option value="T2">T2</option>
                <option value="T3">T3</option>
                <option value="T4">T4</option>
                <option value="T5+">T5+</option>
                <option value="maison">Maison</option>
                <option value="local">Local</option>
                <option value="autre">Autre</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Étage</label>
              <input type="number" {...register('floor')} className={inputCls} placeholder="0" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <div>
              <label className={labelCls}>Bâtiment</label>
              <input {...register('building')} className={inputCls} placeholder="Bât. A" />
            </div>
            <div>
              <label className={labelCls}>Surface (m²)</label>
              <input type="number" step="0.01" {...register('area_sqm')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Pièces</label>
              <input type="number" {...register('rooms')} className={inputCls} />
            </div>
          </div>
        </div>

        {/* Finances */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Finances</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelCls}>Loyer HC (€) <span className="text-red-500">*</span></label>
              <input type="number" step="0.01" min="0" {...register('base_rent')} className={inputCls} />
              {errors.base_rent && <p className={errCls}>{errors.base_rent.message}</p>}
            </div>
            <div>
              <label className={labelCls}>Charges (€)</label>
              <input type="number" step="0.01" min="0" {...register('charges_amount')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Dépôt (mois)</label>
              <input type="number" min="0" {...register('deposit_months')} className={inputCls} />
            </div>
          </div>
        </div>

        {/* État */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_available"
            {...register('is_available')}
            className="w-4 h-4 rounded border-gray-300 text-blue-600"
          />
          <label htmlFor="is_available" className="text-sm text-gray-700 cursor-pointer">
            Logement disponible à la location
          </label>
        </div>

        {/* Notes */}
        <div>
          <label className={labelCls}>Notes</label>
          <textarea {...register('notes')} rows={2} className={`${inputCls} resize-none`} />
        </div>
      </form>
    </Modal>
  )
}
