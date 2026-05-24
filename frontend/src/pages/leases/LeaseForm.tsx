import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { UserRound, Plus, X } from 'lucide-react'
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
  property_id: z.string().min(1, 'Bien immobilier requis'),
  unit_id: z.string().min(1, 'Logement requis'),
  tenant_id: z.string().min(1, 'Locataire requis'),
  lease_type: z.enum(['vide', 'meuble', 'mobilite', 'commercial']),
  start_date: z.string().min(1, 'Date d\'entrée requise'),
  end_date: z.string().optional().or(z.literal('')),
  rent_amount: z.coerce.number().positive('Loyer requis'),
  charges_amount: z.coerce.number().min(0).default(0),
  deposit_amount: z.coerce.number().min(0).default(0),
  payment_day: z.coerce.number().int().min(1).max(28).default(1),
  payment_method: z.enum(['virement', 'cheque', 'prelevement', 'especes']),
  apl_tiers_payant: z.boolean().default(false),
  apl_amount: z.coerce.number().min(0).optional().or(z.literal('')),
  has_guarantor: z.boolean().default(false),
  guarantor_name: z.string().optional(),
  guarantor_phone: z.string().optional(),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

// ─── Inline create-tenant panel — module level to avoid re-mounts ─────────────
interface CreateTenantPanelProps {
  onCreated: (tenant: TenantListItem) => void
  onCancel: () => void
}
function CreateTenantPanel({ onCreated, onCancel }: CreateTenantPanelProps) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handle = async () => {
    if (!firstName.trim() || !lastName.trim()) {
      setError('Prénom et nom sont obligatoires')
      return
    }
    setLoading(true); setError(null)
    try {
      const { data } = await tenantsApi.create({
        first_name: firstName,
        last_name: lastName,
        email: email || undefined,
        phone: phone || undefined,
      })
      onCreated(data as unknown as TenantListItem)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erreur lors de la création')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border border-teal-200 rounded-lg p-3 bg-teal-50 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-teal-700 flex items-center gap-1">
          <UserRound size={13} /> Créer un nouveau locataire
        </span>
        <button type="button" onClick={onCancel} className="text-gray-400 hover:text-gray-600">
          <X size={14} />
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="grid grid-cols-2 gap-2">
        <input value={firstName} onChange={e => setFirstName(e.target.value)} placeholder="Prénom *"
          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
        <input value={lastName} onChange={e => setLastName(e.target.value)} placeholder="Nom *"
          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" type="email"
          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
        <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Téléphone"
          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
      </div>
      <button type="button" onClick={handle} disabled={loading}
        className="w-full py-1.5 text-xs font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 disabled:opacity-50">
        {loading ? 'Création...' : 'Créer le locataire'}
      </button>
    </div>
  )
}

// ─── Main form ────────────────────────────────────────────────────────────────
interface Props {
  lease?: Lease
  onClose: () => void
  onSaved: () => void
  submitError?: string
}

export function LeaseForm({ lease, onClose, onSaved }: Props) {
  const isEdit = !!lease
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [units, setUnits] = useState<UnitOption[]>([])
  const [tenants, setTenants] = useState<TenantListItem[]>([])
  const [loadingUnits, setLoadingUnits] = useState(false)
  const [showCreateTenant, setShowCreateTenant] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: lease ? {
      property_id: lease.property_id,
      unit_id: lease.unit_id,
      tenant_id: lease.tenant_id,
      lease_type: lease.lease_type,
      start_date: lease.start_date,
      end_date: lease.end_date ?? '',
      rent_amount: lease.rent_amount,
      charges_amount: lease.charges_amount,
      deposit_amount: lease.deposit_amount,
      payment_day: lease.payment_day,
      payment_method: lease.payment_method,
      apl_tiers_payant: lease.apl_tiers_payant,
      apl_amount: lease.apl_amount ?? '',
      has_guarantor: lease.has_guarantor,
      guarantor_name: lease.guarantor_name ?? '',
      guarantor_phone: lease.guarantor_phone ?? '',
      notes: lease.notes ?? '',
    } : {
      lease_type: 'vide',
      payment_method: 'virement',
      apl_tiers_payant: false,
      has_guarantor: false,
      payment_day: 1,
      charges_amount: 0,
      deposit_amount: 0,
    },
  })

  const selectedPropertyId = watch('property_id')
  const aplTiersPayant = watch('apl_tiers_payant')
  const hasGuarantor = watch('has_guarantor')

  useEffect(() => {
    propertiesApi.list({ limit: 200 }).then(r => setProperties(r.data.items as PropertyListItem[]))
    tenantsApi.list({ limit: 200 }).then(r => setTenants(r.data.items))
  }, [])

  useEffect(() => {
    if (!selectedPropertyId) { setUnits([]); return }
    setLoadingUnits(true)
    apiClient.get<UnitOption[]>(`/properties/${selectedPropertyId}/units`)
      .then(r => setUnits(r.data))
      .finally(() => setLoadingUnits(false))
    if (!isEdit) setValue('unit_id', '')
  }, [selectedPropertyId, isEdit, setValue])

  const handleTenantCreated = (tenant: TenantListItem) => {
    setTenants(prev => [...prev, tenant])
    setValue('tenant_id', tenant.id, { shouldValidate: true })
    setShowCreateTenant(false)
  }

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    try {
      const payload = {
        ...data,
        end_date: data.end_date || undefined,
        apl_amount: data.apl_amount !== '' && data.apl_tiers_payant ? Number(data.apl_amount) : undefined,
      }
      if (isEdit) {
        await leasesApi.update(lease.id, payload)
      } else {
        await leasesApi.create(payload)
      }
      onSaved()
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setSubmitError(typeof detail === 'string' ? detail : 'Erreur lors de l\'enregistrement du contrat')
    }
  }

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const lbl = 'block text-xs font-medium text-gray-700 mb-1'
  const err = 'mt-1 text-xs text-red-600'

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
          <button onClick={handleSubmit(onSubmit)} disabled={isSubmitting}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {isSubmitting ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Créer le contrat'}
          </button>
        </>
      }
    >
      <form className="space-y-6">
        {submitError && (
          <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {submitError}
          </div>
        )}

        {/* ── Bien & logement ── */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Bien & logement</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={lbl}>Bien immobilier <span className="text-red-500">*</span></label>
              <select {...register('property_id')} className={inp} disabled={isEdit}>
                <option value="">— Sélectionner un bien —</option>
                {properties.map(p => (
                  <option key={p.id} value={p.id}>{p.name} — {p.city}</option>
                ))}
              </select>
              {errors.property_id && <p className={err}>{errors.property_id.message}</p>}
            </div>
            <div>
              <label className={lbl}>Unité / Appartement <span className="text-red-500">*</span></label>
              <select {...register('unit_id')} className={inp} disabled={isEdit || !selectedPropertyId || loadingUnits}>
                <option value="">
                  {loadingUnits ? 'Chargement...' : selectedPropertyId ? '— Sélectionner —' : '← Choisir un bien d\'abord'}
                </option>
                {units.map(u => (
                  <option key={u.id} value={u.id} disabled={u.is_occupied && u.id !== lease?.unit_id}>
                    {u.unit_ref} ({u.unit_type}){u.is_occupied && u.id !== lease?.unit_id ? ' — Occupé' : ` — ${u.base_rent} €/mois`}
                  </option>
                ))}
              </select>
              {errors.unit_id && <p className={err}>{errors.unit_id.message}</p>}
            </div>
          </div>
        </div>

        {/* ── Locataire ── */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Locataire</h3>
          {!showCreateTenant ? (
            <div className="flex gap-2">
              <select {...register('tenant_id')} className={`flex-1 ${inp}`} disabled={isEdit}>
                <option value="">— Sélectionner un locataire —</option>
                {tenants.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.full_name}{t.email ? ` (${t.email})` : ''}
                  </option>
                ))}
              </select>
              {!isEdit && (
                <button type="button" onClick={() => setShowCreateTenant(true)}
                  className="flex items-center gap-1 px-3 py-2 text-xs font-medium text-teal-600 bg-teal-50 border border-teal-200 rounded-lg hover:bg-teal-100 whitespace-nowrap">
                  <Plus size={13} /> Nouveau
                </button>
              )}
            </div>
          ) : (
            <CreateTenantPanel
              onCreated={handleTenantCreated}
              onCancel={() => setShowCreateTenant(false)}
            />
          )}
          {errors.tenant_id && !showCreateTenant && <p className={err}>{errors.tenant_id.message}</p>}
        </div>

        {/* ── Type et dates ── */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Contrat</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={lbl}>Type de bail <span className="text-red-500">*</span></label>
              <select {...register('lease_type')} className={inp}>
                <option value="vide">Location vide</option>
                <option value="meuble">Location meublée</option>
                <option value="mobilite">Bail mobilité</option>
                <option value="commercial">Bail commercial</option>
              </select>
            </div>
            <div>
              <label className={lbl}>Date d'entrée <span className="text-red-500">*</span></label>
              <input type="date" {...register('start_date')} className={inp} />
              {errors.start_date && <p className={err}>{errors.start_date.message}</p>}
            </div>
            <div>
              <label className={lbl}>Date de fin (optionnel)</label>
              <input type="date" {...register('end_date')} className={inp} />
            </div>
          </div>
        </div>

        {/* ── Finances ── */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Finances</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={lbl}>Loyer HC (€) <span className="text-red-500">*</span></label>
              <input type="number" step="0.01" min="0" {...register('rent_amount')} className={inp} placeholder="0.00" />
              {errors.rent_amount && <p className={err}>{errors.rent_amount.message}</p>}
            </div>
            <div>
              <label className={lbl}>Charges (€)</label>
              <input type="number" step="0.01" min="0" {...register('charges_amount')} className={inp} placeholder="0.00" />
            </div>
            <div>
              <label className={lbl}>Dépôt de garantie (€)</label>
              <input type="number" step="0.01" min="0" {...register('deposit_amount')} className={inp} placeholder="0.00" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <label className={lbl}>Jour d'échéance (1–28)</label>
              <input type="number" min="1" max="28" {...register('payment_day')} className={inp} />
            </div>
            <div>
              <label className={lbl}>Mode de paiement</label>
              <select {...register('payment_method')} className={inp}>
                <option value="virement">Virement bancaire</option>
                <option value="cheque">Chèque</option>
                <option value="prelevement">Prélèvement automatique</option>
                <option value="especes">Espèces</option>
              </select>
            </div>
          </div>
        </div>

        {/* ── Aide personnelle au logement ── */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <input type="checkbox" id="apl_tiers_payant" {...register('apl_tiers_payant')}
              className="w-4 h-4 rounded border-gray-300 text-blue-600" />
            <label htmlFor="apl_tiers_payant" className="text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer">
              Aide personnelle au logement — tiers payant CAF
            </label>
          </div>
          {aplTiersPayant && (
            <div className="pl-6">
              <label className={lbl}>Montant aide personnelle au logement mensuel (€)</label>
              <input type="number" step="0.01" min="0" {...register('apl_amount')} className={`${inp} max-w-xs`} placeholder="0.00" />
              <p className="text-xs text-blue-600 mt-1">
                Ce montant sera automatiquement comptabilisé comme pré-payé par la CAF dès la génération de l'avis d'échéance.
              </p>
            </div>
          )}
        </div>

        {/* ── Garant (optionnel) ── */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <input type="checkbox" id="has_guarantor" {...register('has_guarantor')}
              className="w-4 h-4 rounded border-gray-300 text-blue-600" />
            <label htmlFor="has_guarantor" className="text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer">
              Caution solidaire (garant)
            </label>
          </div>
          {hasGuarantor && (
            <div className="grid grid-cols-2 gap-3 pl-6">
              <div>
                <label className={lbl}>Nom du garant</label>
                <input {...register('guarantor_name')} className={inp} />
              </div>
              <div>
                <label className={lbl}>Téléphone</label>
                <input {...register('guarantor_phone')} className={inp} />
              </div>
            </div>
          )}
        </div>

        {/* ── Notes ── */}
        <div>
          <label className={lbl}>Clauses particulières / Notes</label>
          <textarea {...register('notes')} rows={3} className={`${inp} resize-none`} />
        </div>

      </form>
    </Modal>
  )
}
