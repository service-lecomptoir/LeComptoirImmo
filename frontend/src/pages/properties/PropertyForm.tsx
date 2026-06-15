import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { UserRound, Plus, X, AlertTriangle, Building2, MapPin, Ruler, Sparkles, FileText, Home, Store, Boxes } from 'lucide-react'
import { Modal } from '@/components/common/Modal'
import { SectionTitle } from '@/components/common/SectionTitle'
import CommuneAutocomplete from '@/components/common/CommuneAutocomplete'
import AddressAutocomplete from '@/components/common/AddressAutocomplete'
import { propertiesApi } from '@/api/properties'
import { ownersApi } from '@/api/owners'
import { useAuthStore } from '@/store/authStore'
import type { Property } from '@/types/property'
import { TYPOLOGY_OPTIONS, HEATING_OPTIONS, ENERGY_CLASSES, AMENITIES } from '@/types/property'
import type { Owner, OwnerListItem } from '@/types/owner'
import { getErrorMessage } from '@/utils/errors'

const schema = z.object({
  name: z.string().min(1, 'Nom requis'),
  property_type: z.enum(['appartement', 'maison', 'local_commercial', 'autre']),
  address: z.string().min(1, 'Adresse requise'),
  address2: z.string().optional(),
  zip_code: z.string().min(1, 'Code postal requis'),
  city: z.string().min(1, 'Ville requise'),
  country: z.string().default('France'),
  owner_id: z.string().optional(),
  owner_user_id: z.string().optional(),
  // ── Caractéristiques du bien ──────────────────────────────────────────────
  typology: z.string().optional(),
  area_sqm: z.coerce.number().min(0).optional(),
  floor: z.coerce.number().int().optional(),
  bathrooms: z.coerce.number().int().min(0).optional(),
  heating_type: z.string().optional(),
  energy_class: z.string().optional(),
  // ── Équipements & extérieurs ──────────────────────────────────────────────
  furnished: z.boolean().default(false),
  kitchen_equipped: z.boolean().default(false),
  has_elevator: z.boolean().default(false),
  has_balcony: z.boolean().default(false),
  has_terrace: z.boolean().default(false),
  has_garden: z.boolean().default(false),
  has_parking: z.boolean().default(false),
  has_cellar: z.boolean().default(false),
  has_fiber: z.boolean().default(false),
  has_air_conditioning: z.boolean().default(false),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface Props {
  property?: Property
  onClose: () => void
  onSaved: () => void
}

// ─── Create-owner panel — crée une FICHE propriétaire (compte de connexion
//     optionnel, à ajouter ensuite depuis Administration). Module-level pour
//     éviter les pertes de focus au re-render. ───────────────────────────────
interface CreateOwnerPanelProps {
  onCreated: (owner: Owner) => void
  onCancel: () => void
}
function CreateOwnerPanel({ onCreated, onCancel }: CreateOwnerPanelProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handle = async () => {
    if (!name.trim()) {
      setError('Le nom / la dénomination est requis')
      return
    }
    setLoading(true); setError(null)
    try {
      const { data } = await ownersApi.create({
        last_name: name.trim(),
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
      })
      onCreated(data)
    } catch (e: any) {
      setError(getErrorMessage(e, 'Erreur lors de la création'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border border-blue-200 rounded-lg p-3 bg-blue-50 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-blue-700 flex items-center gap-1">
          <UserRound size={13} /> Créer une fiche propriétaire
        </span>
        <button type="button" onClick={onCancel} className="text-gray-400 hover:text-gray-600">
          <X size={14} />
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Nom / SCI *"
        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500" />
      <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" type="email"
        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500" />
      <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Téléphone"
        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500" />
      <button type="button" onClick={handle} disabled={loading}
        className="w-full py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
        {loading ? 'Création...' : 'Créer et lier la fiche'}
      </button>
    </div>
  )
}

// Types de bien présentés en cartes cliquables (plus lisible qu'un <select>).
const PROPERTY_TYPE_CARDS: { value: FormData['property_type']; label: string; icon: typeof Home }[] = [
  { value: 'appartement', label: 'Appartement', icon: Building2 },
  { value: 'maison', label: 'Maison', icon: Home },
  { value: 'local_commercial', label: 'Local commercial', icon: Store },
  { value: 'autre', label: 'Autre', icon: Boxes },
]

// ─── Main form ────────────────────────────────────────────────────────────────
export function PropertyForm({ property, onClose, onSaved }: Props) {
  const isEdit = !!property
  const { user: currentUser } = useAuthStore()
  const isGestionnairePropio = currentUser?.role === 'gestionnaire_proprio'
  const [owners, setOwners] = useState<OwnerListItem[]>([])
  const [showCreateOwner, setShowCreateOwner] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, watch, setValue, setError, clearErrors, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: property ? {
      name: property.name,
      property_type: property.property_type,
      address: property.address,
      address2: property.address2 ?? '',
      zip_code: property.zip_code,
      city: property.city,
      country: property.country ?? 'France',
      owner_id: property.owner_id ?? '',
      typology: property.typology ?? '',
      area_sqm: property.area_sqm ?? undefined,
      floor: property.floor ?? undefined,
      bathrooms: property.bathrooms ?? undefined,
      heating_type: property.heating_type ?? '',
      energy_class: property.energy_class ?? '',
      furnished: property.furnished ?? false,
      kitchen_equipped: property.kitchen_equipped ?? false,
      has_elevator: property.has_elevator ?? false,
      has_balcony: property.has_balcony ?? false,
      has_terrace: property.has_terrace ?? false,
      has_garden: property.has_garden ?? false,
      has_parking: property.has_parking ?? false,
      has_cellar: property.has_cellar ?? false,
      has_fiber: property.has_fiber ?? false,
      has_air_conditioning: property.has_air_conditioning ?? false,
      notes: property.notes ?? '',
    } : {
      property_type: 'appartement',
      country: 'France',
      owner_id: '',
      furnished: false,
      kitchen_equipped: false,
      has_elevator: false,
      has_balcony: false,
      has_terrace: false,
      has_garden: false,
      has_parking: false,
      has_cellar: false,
    },
  })

  const selectedOwnerId = watch('owner_id')

  // Adresse / code postal / ville sont pilotés par les autocomplétions (setValue)
  // → on les enregistre manuellement auprès de react-hook-form.
  useEffect(() => {
    register('property_type')
    register('address')
    register('zip_code')
    register('city')
  }, [register])

  useEffect(() => {
    if (isGestionnairePropio) return
    ownersApi.list({ limit: 200 })
      .then(r => setOwners(r.data.items))
      .catch(() => {})
  }, [isGestionnairePropio])

  const handleOwnerCreated = (owner: Owner) => {
    setOwners(prev => [{ ...owner } as OwnerListItem, ...prev])
    setValue('owner_id', owner.id, { shouldValidate: true })
    clearErrors('owner_id')
    setShowCreateOwner(false)
  }

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    // Le gestionnaire-propriétaire est lui-même le propriétaire (rattaché côté
    // serveur à sa propre fiche). Sinon une fiche propriétaire est obligatoire.
    if (!isGestionnairePropio && !data.owner_id) {
      setError('owner_id', { message: 'Propriétaire requis' })
      return
    }
    const payload = {
      name: data.name,
      property_type: data.property_type,
      address: data.address,
      address2: data.address2 || null,
      zip_code: data.zip_code,
      city: data.city,
      country: data.country,
      ...(isGestionnairePropio
        ? { owner_user_id: currentUser?.id }
        : { owner_id: data.owner_id }),
      typology: data.typology || null,
      area_sqm: data.area_sqm ?? null,
      floor: data.floor ?? null,
      bathrooms: data.bathrooms ?? null,
      heating_type: data.heating_type || null,
      energy_class: data.energy_class || null,
      furnished: data.furnished,
      kitchen_equipped: data.kitchen_equipped,
      has_elevator: data.has_elevator,
      has_balcony: data.has_balcony,
      has_terrace: data.has_terrace,
      has_garden: data.has_garden,
      has_parking: data.has_parking,
      has_cellar: data.has_cellar,
      has_fiber: data.has_fiber,
      has_air_conditioning: data.has_air_conditioning,
      notes: data.notes || undefined,
    }
    try {
      if (isEdit) {
        await propertiesApi.update(property.id, payload)
      } else {
        await propertiesApi.create(payload)
      }
      onSaved()
    } catch (e: any) {
      // Erreurs serveur : limite d'offre atteinte (400), licence absente /
      // suspendue (403), service indisponible (503), validation, etc.
      setSubmitError(getErrorMessage(
        e,
        "Une erreur est survenue lors de l'enregistrement. Vérifiez votre offre puis réessayez.",
      ))
    }
  }

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const lbl = 'block text-xs font-medium text-gray-700 mb-1'
  const err = 'mt-1 text-xs text-red-600'

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? 'Modifier le bien' : 'Nouveau bien immobilier'}
      size="md"
      footer={
        <>
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
            Annuler
          </button>
          <button onClick={handleSubmit(onSubmit)} disabled={isSubmitting}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {isSubmitting ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Créer'}
          </button>
        </>
      }
    >
      <form className="space-y-5">
        {submitError && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5">
            <AlertTriangle size={15} className="text-red-500 shrink-0 mt-0.5" />
            <p className="text-xs text-red-700">{submitError}</p>
          </div>
        )}
        {/* Identification */}
        <div>
          <div className="mb-4">
            <label className={lbl}>Nom du bien <span className="text-red-500">*</span></label>
            <input {...register('name')} className={inp} placeholder="ex. Résidence Les Acacias, Appt 3B..." />
            {errors.name && <p className={err}>{errors.name.message}</p>}
          </div>
          <label className={lbl}>Type de bien <span className="text-red-500">*</span></label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {PROPERTY_TYPE_CARDS.map(({ value, label, icon: Icon }) => {
              const active = watch('property_type') === value
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setValue('property_type', value, { shouldValidate: true })}
                  className={`flex flex-col items-center gap-1.5 px-3 py-3 rounded-lg border text-xs font-medium transition-colors ${
                    active
                      ? 'border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-200'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <Icon size={18} className={active ? 'text-blue-600' : 'text-gray-400'} />
                  {label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Adresse */}
        <div>
          <SectionTitle icon={MapPin}>Adresse</SectionTitle>
          <div className="space-y-3">
            <div>
              <label className={lbl}>Adresse <span className="text-red-500">*</span></label>
              <AddressAutocomplete
                value={watch('address') || ''}
                onChange={v => { setValue('address', v, { shouldValidate: true }); clearErrors('address') }}
                onSelect={({ street, postcode, city }) => {
                  setValue('address', street, { shouldValidate: true })
                  if (postcode) setValue('zip_code', postcode, { shouldValidate: true })
                  if (city) setValue('city', city, { shouldValidate: true })
                  clearErrors(['address', 'zip_code', 'city'])
                }}
                className={inp}
                placeholder="10 rue de la Paix"
              />
              {errors.address && <p className={err}>{errors.address.message}</p>}
            </div>
            <div>
              <label className={lbl}>Complément d'adresse</label>
              <input {...register('address2')} className={inp} placeholder="Appartement 11, Bât. B, étage 3…" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className={lbl}>Code postal <span className="text-red-500">*</span></label>
                <CommuneAutocomplete
                  value={watch('zip_code') || ''}
                  onChange={v => { setValue('zip_code', v, { shouldValidate: true }); clearErrors('zip_code') }}
                  onSelect={({ zip, city }) => {
                    setValue('zip_code', zip, { shouldValidate: true })
                    setValue('city', city, { shouldValidate: true })
                    clearErrors(['zip_code', 'city'])
                  }}
                  display="postcode"
                  className={inp}
                  placeholder="ex. 75001"
                />
                {errors.zip_code && <p className={err}>{errors.zip_code.message}</p>}
              </div>
              <div>
                <label className={lbl}>Ville <span className="text-red-500">*</span></label>
                <CommuneAutocomplete
                  value={watch('city') || ''}
                  onChange={v => { setValue('city', v, { shouldValidate: true }); clearErrors('city') }}
                  onSelect={({ zip, city }) => {
                    setValue('zip_code', zip, { shouldValidate: true })
                    setValue('city', city, { shouldValidate: true })
                    clearErrors(['zip_code', 'city'])
                  }}
                  display="city"
                  className={inp}
                  placeholder="ex. Paris"
                />
                {errors.city && <p className={err}>{errors.city.message}</p>}
              </div>
              <div>
                <label className={lbl}>Pays</label>
                <input {...register('country')} className={inp} />
              </div>
            </div>
          </div>
        </div>

        {/* Caractéristiques du bien */}
        <div>
          <SectionTitle icon={Ruler}>Caractéristiques</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <label className={lbl}>Type (nombre de pièces)</label>
              <select {...register('typology')} className={inp}>
                <option value="">— Sélectionner —</option>
                {TYPOLOGY_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className={lbl}>Surface (m²)</label>
              <input type="number" step="0.01" {...register('area_sqm')} className={inp} placeholder="ex. 45" />
            </div>
            <div>
              <label className={lbl}>Étage</label>
              <input type="number" {...register('floor')} className={inp} placeholder="ex. 2" />
            </div>
            <div>
              <label className={lbl}>Salle d'eau / salle de bain</label>
              <select {...register('bathrooms')} className={inp}>
                <option value="">— Sélectionner —</option>
                {[0, 1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className={lbl}>Chauffage</label>
              <select {...register('heating_type')} className={inp}>
                <option value="">— Sélectionner —</option>
                {HEATING_OPTIONS.map(h => <option key={h.value} value={h.value}>{h.label}</option>)}
              </select>
            </div>
            <div>
              <label className={lbl}>Classe énergie (DPE)</label>
              <select {...register('energy_class')} className={inp}>
                <option value="">— Sélectionner —</option>
                {ENERGY_CLASSES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Équipements & extérieurs */}
        <div>
          <SectionTitle icon={Sparkles}>Équipements & extérieurs</SectionTitle>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {AMENITIES.map(a => (
              <label key={a.key} className="flex items-center gap-2 px-2.5 py-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 text-xs text-gray-700">
                <input type="checkbox" {...register(a.key)} className="w-4 h-4 shrink-0 rounded border-gray-300 text-blue-600" />
                <span className="min-w-0 leading-tight">{a.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Propriétaire */}
        {isGestionnairePropio ? (
          <div className="px-3 py-2 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700 flex items-center gap-2">
            <UserRound size={13} />
            Vous êtes le propriétaire de ce bien
          </div>
        ) : (
          <div>
            <SectionTitle icon={UserRound}>
              Propriétaire <span className="text-red-500 font-normal normal-case">*</span>
            </SectionTitle>

            {!showCreateOwner ? (
              <div className="flex gap-2">
                <select
                  value={selectedOwnerId || ''}
                  onChange={e => { setValue('owner_id', e.target.value, { shouldValidate: true }); clearErrors('owner_id') }}
                  className={`flex-1 ${inp}`}
                >
                  <option value="">— Sélectionner un propriétaire —</option>
                  {owners.map(o => (
                    <option key={o.id} value={o.id}>{o.full_name}{o.email ? ` (${o.email})` : ''}</option>
                  ))}
                </select>
                <button type="button" onClick={() => setShowCreateOwner(true)}
                  className="flex items-center gap-1 px-3 py-2 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 whitespace-nowrap">
                  <Plus size={13} /> Nouveau
                </button>
              </div>
            ) : (
              <CreateOwnerPanel
                onCreated={handleOwnerCreated}
                onCancel={() => setShowCreateOwner(false)}
              />
            )}

            {errors.owner_id && !showCreateOwner && (
              <p className={err}>{errors.owner_id.message}</p>
            )}
            {selectedOwnerId && !showCreateOwner && (
              <p className="mt-1 text-xs text-green-600 flex items-center gap-1">
                <UserRound size={11} /> Fiche propriétaire rattachée à ce bien
              </p>
            )}
          </div>
        )}

        {/* Notes */}
        <div>
          <SectionTitle icon={FileText}>Notes internes</SectionTitle>
          <textarea {...register('notes')} rows={2}
            className={`${inp} resize-none`} placeholder="Informations internes (non visibles par le locataire)…" />
        </div>
      </form>
    </Modal>
  )
}
