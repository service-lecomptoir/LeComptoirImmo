import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/common/Modal'
import { leasesApi } from '@/api/leases'
import { propertiesApi } from '@/api/properties'
import { tenantsApi } from '@/api/tenants'
import { apiClient } from '@/api/client'
import type { Lease } from '@/types/lease'
import type { PropertyListItem } from '@/types/property'
import type { TenantListItem } from '@/types/tenant'

interface UnitOption {
  id: string
  unit_ref: string
  unit_type: string
  base_rent: number
  charges_amount: number
  is_occupied: boolean
}

const schema = z.object({
  property_id: z.string().min(1, 'Bien requis'),
  unit_id: z.string().min(1, 'Logement requis'),
  tenant_id: z.string().min(1, 'Locataire requis'),
  lease_type: z.enum(['vide', 'meuble', 'mobilite', 'commercial']),
  start_date: z.string().min(1, 'Date de début requise'),
  end_date: z.string().optional().or(z.literal('')),
  notice_date: z.string().optional().or(z.literal('')),
  rent_amount: z.coerce.number().positive('Loyer requis'),
  charges_amount: z.coerce.number().min(0).default(0),
  deposit_amount: z.coerce.number().min(0).default(0),
  payment_day: z.coerce.number().int().min(1).max(28).default(1),
  payment_method: z.enum(['virement', 'cheque', 'prelevement', 'especes']),
  apl_amount: z.coerce.number().min(0).optional().or(z.literal('')),
  apl_tiers_payant: z.boolean().default(false),
  has_guarantor: z.boolean().default(false),
  guarantor_name: z.string().optional(),
  guarantor_email: z.string().optional(),
  guarantor_phone: z.string().optional(),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface Props {
  lease?: Lease
  onClose: () => void
  onSaved: () => void
}

export function LeaseForm({ lease, onClose, onSaved }: Props) {
  const isEdit = !!lease
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [units, setUnits] = useState<UnitOption[]>([])
  const [tenants, setTenants] = useState<TenantListItem[]>([])
  const [loadingUnits, setLoadingUnits] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: lease
      ? {
          property_id: lease.property_id,
          unit_id: lease.unit_id,
          tenant_id: lease.tenant_id,
          lease_type: lease.lease_type,
          start_date: lease.start_date,
          end_date: lease.end_date ?? '',
          notice_date: lease.notice_date ?? '',
          rent_amount: lease.rent_amount,
          charges_amount: lease.charges_amount,
          deposit_amount: lease.deposit_amount,
          payment_day: lease.payment_day,
          payment_method: lease.payment_method,
          apl_amount: lease.apl_amount ?? '',
          apl_tiers_payant: lease.apl_tiers_payant,
          has_guarantor: lease.has_guarantor,
          guarantor_name: lease.guarantor_name ?? '',
          guarantor_email: lease.guarantor_email ?? '',
          guarantor_phone: lease.guarantor_phone ?? '',
          notes: lease.notes ?? '',
        }
      : {
          lease_type: 'vide',
          payment_method: 'virement',
          apl_tiers_payant: false,
          has_guarantor: false,
          payment_day: 1,
        },
  })

  const selectedPropertyId = watch('property_id')
  const hasGuarantor = watch('has_guarantor')
  watch('apl_tiers_payant')

  // Charger biens et locataires
  useEffect(() => {
    propertiesApi.list({ limit: 200 }).then(r => setProperties(r.data.items as PropertyListItem[]))
    tenantsApi.list({ limit: 200 }).then(r => setTenants(r.data.items))
  }, [])

  // Charger logements selon le bien sélectionné
  useEffect(() => {
    if (!selectedPropertyId) { setUnits([]); return }
    setLoadingUnits(true)
    apiClient
      .get<UnitOption[]>(`/properties/${selectedPropertyId}/units`)
      .then(r => setUnits(r.data))
      .finally(() => setLoadingUnits(false))
    if (!isEdit) setValue('unit_id', '')
  }, [selectedPropertyId, isEdit, setValue])

  const onSubmit = async (data: FormData) => {
    const payload = {
      ...data,
      end_date: data.end_date || undefined,
      notice_date: data.notice_date || undefined,
      apl_amount: data.apl_amount !== '' ? Number(data.apl_amount) : undefined,
    }
    if (isEdit) {
      await leasesApi.update(lease.id, payload)
    } else {
      await leasesApi.create(payload)
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
      title={isEdit ? 'Modifier le contrat' : 'Nouveau contrat de bail'}
      size="xl"
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
            {isSubmitting ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Créer le contrat'}
          </button>
        </>
      }
    >
      <form className="space-y-6">

        {/* Logement */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Logement</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Bien immobilier <span className="text-red-500">*</span></label>
              <select {...register('property_id')} className={inputCls} disabled={isEdit}>
                <option value="">— Sélectionner un bien —</option>
                {properties.map(p => (
                  <option key={p.id} value={p.id}>{p.name} — {p.city}</option>
                ))}
              </select>
              {errors.property_id && <p className={errCls}>{errors.property_id.message}</p>}
            </div>
            <div>
              <label className={labelCls}>Logement <span className="text-red-500">*</span></label>
              <select
                {...register('unit_id')}
                className={inputCls}
                disabled={isEdit || !selectedPropertyId || loadingUnits}
              >
                <option value="">
                  {loadingUnits ? 'Chargement...' : '— Sélectionner un logement —'}
                </option>
                {units.map(u => (
                  <option key={u.id} value={u.id} disabled={u.is_occupied && u.id !== lease?.unit_id}>
                    {u.unit_ref} ({u.unit_type})
                    {u.is_occupied ? ' — Occupé' : ` — ${u.base_rent} €/mois`}
                  </option>
                ))}
              </select>
              {errors.unit_id && <p className={errCls}>{errors.unit_id.message}</p>}
            </div>
          </div>
        </div>

        {/* Locataire */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Locataire</h3>
          <div>
            <label className={labelCls}>Locataire <span className="text-red-500">*</span></label>
            <select {...register('tenant_id')} className={inputCls} disabled={isEdit}>
              <option value="">— Sélectionner un locataire —</option>
              {tenants.map(t => (
                <option key={t.id} value={t.id}>{t.full_name}{t.email ? ` (${t.email})` : ''}</option>
              ))}
            </select>
            {errors.tenant_id && <p className={errCls}>{errors.tenant_id.message}</p>}
          </div>
        </div>

        {/* Type et dates */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Contrat</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Type de bail <span className="text-red-500">*</span></label>
              <select {...register('lease_type')} className={inputCls}>
                <option value="vide">Location vide</option>
                <option value="meuble">Location meublée</option>
                <option value="mobilite">Bail mobilité</option>
                <option value="commercial">Bail commercial</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Date d'entrée <span className="text-red-500">*</span></label>
              <input type="date" {...register('start_date')} className={inputCls} />
              {errors.start_date && <p className={errCls}>{errors.start_date.message}</p>}
            </div>
            <div>
              <label className={labelCls}>Date de fin (optionnel)</label>
              <input type="date" {...register('end_date')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Date de congé (optionnel)</label>
              <input type="date" {...register('notice_date')} className={inputCls} />
            </div>
          </div>
        </div>

        {/* Finances */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Finances</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelCls}>Loyer HC (€) <span className="text-red-500">*</span></label>
              <input type="number" step="0.01" min="0" {...register('rent_amount')} className={inputCls} />
              {errors.rent_amount && <p className={errCls}>{errors.rent_amount.message}</p>}
            </div>
            <div>
              <label className={labelCls}>Charges (€)</label>
              <input type="number" step="0.01" min="0" {...register('charges_amount')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Dépôt de garantie (€)</label>
              <input type="number" step="0.01" min="0" {...register('deposit_amount')} className={inputCls} />
            </div>
          </div>
        </div>

        {/* Paiement */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Paiement</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Jour du mois (1–28)</label>
              <input type="number" min="1" max="28" {...register('payment_day')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Mode de paiement</label>
              <select {...register('payment_method')} className={inputCls}>
                <option value="virement">Virement bancaire</option>
                <option value="cheque">Chèque</option>
                <option value="prelevement">Prélèvement automatique</option>
                <option value="especes">Espèces</option>
              </select>
            </div>
          </div>
        </div>

        {/* APL */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">APL</h3>
          <div className="grid grid-cols-2 gap-3 items-end">
            <div>
              <label className={labelCls}>Montant APL mensuel (€)</label>
              <input type="number" step="0.01" min="0" {...register('apl_amount')} className={inputCls} placeholder="0.00" />
            </div>
            <div className="flex items-center gap-2 pb-1">
              <input
                type="checkbox"
                id="apl_tiers_payant"
                {...register('apl_tiers_payant')}
                className="w-4 h-4 rounded border-gray-300 text-blue-600"
              />
              <label htmlFor="apl_tiers_payant" className="text-sm text-gray-700 cursor-pointer">
                Tiers-payant (versement CAF direct au bailleur)
              </label>
            </div>
          </div>
        </div>

        {/* Garant */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <input
              type="checkbox"
              id="has_guarantor"
              {...register('has_guarantor')}
              className="w-4 h-4 rounded border-gray-300 text-blue-600"
            />
            <label htmlFor="has_guarantor" className="text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer">
              Caution solidaire (garant)
            </label>
          </div>
          {hasGuarantor && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelCls}>Nom du garant</label>
                <input {...register('guarantor_name')} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Email</label>
                <input type="email" {...register('guarantor_email')} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Téléphone</label>
                <input {...register('guarantor_phone')} className={inputCls} />
              </div>
            </div>
          )}
        </div>

        {/* Notes */}
        <div>
          <label className={labelCls}>Clauses particulières / Notes</label>
          <textarea {...register('notes')} rows={3} className={`${inputCls} resize-none`} />
        </div>
      </form>
    </Modal>
  )
}
