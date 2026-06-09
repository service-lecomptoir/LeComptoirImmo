import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { UserRound, Plus, X, Building2, Users, FileSignature, Euro } from 'lucide-react'
import { Modal } from '@/components/common/Modal'
import { SectionTitle } from '@/components/common/SectionTitle'
import { PhoneInput } from '@/components/common/PhoneInput'
import { leasesApi } from '@/api/leases'
import { propertiesApi } from '@/api/properties'
import { tenantsApi } from '@/api/tenants'
import type { Lease } from '@/types/lease'
import type { PropertyListItem } from '@/types/property'
import type { TenantListItem } from '@/types/tenant'

const schema = z.object({
  property_id: z.string().min(1, 'Bien immobilier requis'),
  tenant_id: z.string().min(1, 'Locataire requis'),
  lease_type: z.enum(['vide', 'meuble', 'mobilite', 'commercial']),
  start_date: z.string().min(1, 'Date d\'entrée requise'),
  end_date: z.string().optional().or(z.literal('')),
  rent_amount: z.coerce.number().positive('Loyer requis'),
  charges_amount: z.coerce.number().min(0).default(0),
  deposit_amount: z.coerce.number().min(0).default(0),
  payment_day: z.coerce.number().int().min(1).max(28).default(1),
  payment_method: z.enum(['virement', 'cheque', 'prelevement', 'especes']).default('virement'),
  rent_call_rule: z.enum(['contractuelle', 'calendrier']).default('calendrier'),
  payment_frequency: z.enum(['mensuelle', 'bimestrielle', 'trimestrielle', 'semestrielle', 'annuelle']).default('mensuelle'),
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
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <input value={firstName} onChange={e => setFirstName(e.target.value)} placeholder="Prénom *"
          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
        <input value={lastName} onChange={e => setLastName(e.target.value)} placeholder="Nom *"
          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" type="email"
          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
        <PhoneInput value={phone} onChange={setPhone}
          inputClassName="flex-1 w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500" />
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
  const [tenants, setTenants] = useState<TenantListItem[]>([])
  const [showCreateTenant, setShowCreateTenant] = useState(false)
  const [showCreateCoTenant, setShowCreateCoTenant] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [secondaryIds, setSecondaryIds] = useState<string[]>(
    lease?.co_tenants?.map(t => t.id) ?? []
  )

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: lease ? {
      property_id: lease.property_id,
      tenant_id: lease.tenant_id,
      lease_type: lease.lease_type,
      start_date: lease.start_date,
      end_date: lease.end_date ?? '',
      rent_amount: lease.rent_amount,
      charges_amount: lease.charges_amount,
      deposit_amount: lease.deposit_amount,
      payment_day: lease.payment_day,
      payment_method: lease.payment_method,
      rent_call_rule: lease.rent_call_rule ?? 'calendrier',
      payment_frequency: lease.payment_frequency ?? 'mensuelle',
      apl_tiers_payant: lease.apl_tiers_payant,
      apl_amount: lease.apl_amount ?? '',
      has_guarantor: lease.has_guarantor,
      guarantor_name: lease.guarantor_name ?? '',
      guarantor_phone: lease.guarantor_phone ?? '',
      notes: lease.notes ?? '',
    } : {
      lease_type: 'vide',
      payment_method: 'virement',
      rent_call_rule: 'calendrier',
      payment_frequency: 'mensuelle',
      apl_tiers_payant: false,
      has_guarantor: false,
      payment_day: 1,
      charges_amount: 0,
      deposit_amount: 0,
    },
  })

  const aplTiersPayant = watch('apl_tiers_payant')
  const hasGuarantor = watch('has_guarantor')

  useEffect(() => {
    // En édition, les <select> sont rendus avant l'arrivée des options : on ré-applique
    // les valeurs une fois les listes chargées pour que le bien et le locataire s'affichent.
    propertiesApi.list({ limit: 200 }).then(r => {
      setProperties(r.data.items as PropertyListItem[])
      if (lease) setValue('property_id', lease.property_id)
    })
    tenantsApi.list({ limit: 200, available_only: !isEdit }).then(r => {
      setTenants(r.data.items)
      if (lease) setValue('tenant_id', lease.tenant_id)
    })
  }, [])

  const handleTenantCreated = (tenant: TenantListItem) => {
    setTenants(prev => [...prev, tenant])
    setValue('tenant_id', tenant.id, { shouldValidate: true })
    setShowCreateTenant(false)
  }

  const handleCoTenantCreated = (tenant: TenantListItem) => {
    setTenants(prev => prev.some(t => t.id === tenant.id) ? prev : [...prev, tenant])
    setSecondaryIds(prev => prev.includes(tenant.id) ? prev : [...prev, tenant.id])
    setShowCreateCoTenant(false)
  }

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    try {
      const payload = {
        ...data,
        end_date: data.end_date || undefined,
        apl_amount: data.apl_amount !== '' && data.apl_tiers_payant ? Number(data.apl_amount) : undefined,
        secondary_tenant_ids: secondaryIds,
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
          <SectionTitle icon={Building2}>Bien immobilier</SectionTitle>
          <div>
            <label className={lbl}>Bien immobilier <span className="text-red-500">*</span></label>
            <select
              value={watch('property_id') || ''}
              onChange={e => setValue('property_id', e.target.value, { shouldValidate: true })}
              className={inp}
              disabled={isEdit}
            >
              <option value="">— Sélectionner un bien —</option>
              {properties
                .filter(p => isEdit || !p.is_occupied)
                .map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
            </select>
            {errors.property_id && <p className={err}>{errors.property_id.message}</p>}
          </div>
        </div>

        {/* ── Locataire ── */}
        <div>
          <SectionTitle icon={UserRound}>Locataire</SectionTitle>
          {!showCreateTenant ? (
            <div className="flex gap-2">
              <select
                value={watch('tenant_id') || ''}
                onChange={e => setValue('tenant_id', e.target.value, { shouldValidate: true })}
                className={`flex-1 ${inp}`}
              >
                <option value="">— Sélectionner un locataire —</option>
                {tenants.map(t => (
                  <option key={t.id} value={t.id}>{t.full_name}</option>
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

        {/* ── Co-titulaires (optionnel) ── */}
        <div>
          <SectionTitle icon={Users}>Co-titulaires (optionnel)</SectionTitle>
          <p className="text-xs text-gray-400 mb-2">
            Locataires secondaires, solidaires du bail. Ils apparaîtront sur l'avis d'échéance, la quittance et le bail.
          </p>
          {!showCreateCoTenant ? (
            <div className="flex gap-2">
              <select
                value=""
                onChange={(e) => {
                  const id = e.target.value
                  if (id) setSecondaryIds(prev => prev.includes(id) ? prev : [...prev, id])
                }}
                className={`flex-1 ${inp}`}
              >
                <option value="">— Ajouter un co-titulaire existant —</option>
                {tenants
                  .filter(t => t.id !== watch('tenant_id') && !secondaryIds.includes(t.id))
                  .map(t => (
                    <option key={t.id} value={t.id}>{t.full_name}</option>
                  ))}
              </select>
              <button type="button" onClick={() => setShowCreateCoTenant(true)}
                className="flex items-center gap-1 px-3 py-2 text-xs font-medium text-teal-600 bg-teal-50 border border-teal-200 rounded-lg hover:bg-teal-100 whitespace-nowrap">
                <Plus size={13} /> Nouveau
              </button>
            </div>
          ) : (
            <CreateTenantPanel
              onCreated={handleCoTenantCreated}
              onCancel={() => setShowCreateCoTenant(false)}
            />
          )}
          {secondaryIds.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {secondaryIds.map(id => {
                const t = tenants.find(x => x.id === id)
                return (
                  <span key={id} className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs">
                    {t?.full_name ?? id}
                    <button type="button" onClick={() => setSecondaryIds(prev => prev.filter(x => x !== id))}
                      className="text-blue-400 hover:text-blue-700">
                      <X size={12} />
                    </button>
                  </span>
                )
              })}
            </div>
          )}
        </div>

        {/* ── Type et dates ── */}
        <div>
          <SectionTitle icon={FileSignature}>Contrat</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
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
          <SectionTitle icon={Euro}>Finances</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
            <div>
              <label className={lbl}>Jour de paiement</label>
              <input type="number" min="1" max="28" {...register('payment_day')} className={inp} />
              <p className="text-xs text-gray-400 mt-1">Jour du mois où le loyer est exigible — c'est l'échéance affichée sur l'avis (ex. 6).</p>
            </div>
            <div>
              <label className={lbl}>Fréquence de paiement</label>
              <select {...register('payment_frequency')} className={inp}>
                <option value="mensuelle">Mensuelle</option>
                <option value="bimestrielle">Bimestrielle</option>
                <option value="trimestrielle">Trimestrielle</option>
                <option value="semestrielle">Semestrielle</option>
                <option value="annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label className={lbl}>Règle d'appel de loyer</label>
              <select {...register('rent_call_rule')} className={inp}>
                <option value="calendrier">Période calendrier (1er → fin de mois)</option>
                <option value="contractuelle">Période contractuelle (date à date du bail)</option>
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
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-6">
              <div>
                <label className={lbl}>Nom du garant</label>
                <input {...register('guarantor_name')} className={inp} />
              </div>
              <div>
                <label className={lbl}>Téléphone</label>
                <PhoneInput value={watch('guarantor_phone') || ''} onChange={v => setValue('guarantor_phone', v)} />
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
