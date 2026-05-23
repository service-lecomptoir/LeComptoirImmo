import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { UserRound, Plus, X } from 'lucide-react'
import { Modal } from '@/components/common/Modal'
import { propertiesApi } from '@/api/properties'
import { usersApi } from '@/api/users'
import type { Property } from '@/types/property'
import type { User } from '@/types/auth'

const schema = z.object({
  name: z.string().min(1, 'Nom requis'),
  property_type: z.enum(['immeuble', 'maison', 'appartement', 'local_commercial', 'autre']),
  address: z.string().min(1, 'Adresse requise'),
  zip_code: z.string().min(1, 'Code postal requis'),
  city: z.string().min(1, 'Ville requise'),
  country: z.string().default('France'),
  owner_user_id: z.string().uuid('Propriétaire requis').min(1, 'Propriétaire requis'),
  notes: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface Props {
  property?: Property
  onClose: () => void
  onSaved: () => void
}

// ─── Create-owner panel — at module level to avoid focus-loss re-mounts ───────
interface CreateOwnerPanelProps {
  onCreated: (user: User) => void
  onCancel: () => void
}
function CreateOwnerPanel({ onCreated, onCancel }: CreateOwnerPanelProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handle = async () => {
    if (!name.trim() || !email.trim() || !password.trim()) {
      setError('Tous les champs sont requis')
      return
    }
    setLoading(true); setError(null)
    try {
      const { data } = await usersApi.create({ full_name: name, email, password, role: 'proprietaire' })
      onCreated(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erreur lors de la création')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border border-blue-200 rounded-lg p-3 bg-blue-50 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-blue-700 flex items-center gap-1">
          <UserRound size={13} /> Créer un compte propriétaire
        </span>
        <button type="button" onClick={onCancel} className="text-gray-400 hover:text-gray-600">
          <X size={14} />
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Nom complet *"
        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500" />
      <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email *" type="email"
        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500" />
      <input value={password} onChange={e => setPassword(e.target.value)} placeholder="Mot de passe *" type="password"
        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500" />
      <button type="button" onClick={handle} disabled={loading}
        className="w-full py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
        {loading ? 'Création...' : 'Créer et lier le compte'}
      </button>
    </div>
  )
}

// ─── Main form ────────────────────────────────────────────────────────────────
export function PropertyForm({ property, onClose, onSaved }: Props) {
  const isEdit = !!property
  const [proprietaires, setProprietaires] = useState<User[]>([])
  const [showCreateOwner, setShowCreateOwner] = useState(false)

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: property ? {
      name: property.name,
      property_type: property.property_type,
      address: property.address,
      zip_code: property.zip_code,
      city: property.city,
      country: property.country ?? 'France',
      owner_user_id: property.owner_user_id ?? '',
      notes: property.notes ?? '',
    } : { property_type: 'appartement', country: 'France' },
  })

  const selectedOwnerId = watch('owner_user_id')

  useEffect(() => {
    usersApi.list({ role: 'proprietaire' })
      .then(r => setProprietaires(r.data))
      .catch(() => {})
  }, [])

  const handleOwnerCreated = (user: User) => {
    setProprietaires(prev => [...prev, user])
    setValue('owner_user_id', user.id, { shouldValidate: true })
    setShowCreateOwner(false)
  }

  const onSubmit = async (data: FormData) => {
    const payload = {
      name: data.name,
      property_type: data.property_type,
      address: data.address,
      zip_code: data.zip_code,
      city: data.city,
      country: data.country,
      owner_user_id: data.owner_user_id,
      notes: data.notes || undefined,
    }
    if (isEdit) {
      await propertiesApi.update(property.id, payload)
    } else {
      await propertiesApi.create(payload)
    }
    onSaved()
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
        {/* Identification */}
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className={lbl}>Nom du bien <span className="text-red-500">*</span></label>
            <input {...register('name')} className={inp} placeholder="ex. Résidence Les Acacias, Appt 3B..." />
            {errors.name && <p className={err}>{errors.name.message}</p>}
          </div>
          <div>
            <label className={lbl}>Type de bien <span className="text-red-500">*</span></label>
            <select {...register('property_type')} className={inp}>
              <option value="appartement">Appartement</option>
              <option value="maison">Maison</option>
              <option value="immeuble">Immeuble</option>
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
              <label className={lbl}>Adresse <span className="text-red-500">*</span></label>
              <input {...register('address')} className={inp} placeholder="10 rue de la Paix" />
              {errors.address && <p className={err}>{errors.address.message}</p>}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={lbl}>Code postal <span className="text-red-500">*</span></label>
                <input {...register('zip_code')} className={inp} />
                {errors.zip_code && <p className={err}>{errors.zip_code.message}</p>}
              </div>
              <div>
                <label className={lbl}>Ville <span className="text-red-500">*</span></label>
                <input {...register('city')} className={inp} />
                {errors.city && <p className={err}>{errors.city.message}</p>}
              </div>
              <div>
                <label className={lbl}>Pays</label>
                <input {...register('country')} className={inp} />
              </div>
            </div>
          </div>
        </div>

        {/* Propriétaire — obligatoire */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Propriétaire <span className="text-red-500 font-normal normal-case">*</span>
          </h3>

          {!showCreateOwner ? (
            <div className="flex gap-2">
              <select
                value={selectedOwnerId || ''}
                onChange={e => setValue('owner_user_id', e.target.value, { shouldValidate: true })}
                className={`flex-1 ${inp}`}
              >
                <option value="">— Sélectionner un propriétaire —</option>
                {proprietaires.map(u => (
                  <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
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

          {errors.owner_user_id && !showCreateOwner && (
            <p className={err}>{errors.owner_user_id.message}</p>
          )}
          {selectedOwnerId && !showCreateOwner && (
            <p className="mt-1 text-xs text-green-600 flex items-center gap-1">
              <UserRound size={11} /> Le propriétaire pourra se connecter et voir ce bien
            </p>
          )}
        </div>

        {/* Notes */}
        <div>
          <label className={lbl}>Notes</label>
          <textarea {...register('notes')} rows={2}
            className={`${inp} resize-none`} />
        </div>
      </form>
    </Modal>
  )
}
