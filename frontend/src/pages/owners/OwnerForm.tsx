import { useState, useEffect } from 'react'
import { useForm, UseFormRegister, FieldErrors } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Contact, Phone, Landmark, UserRound, Plus, X } from 'lucide-react'
import { SectionTitle } from '@/components/common/SectionTitle'
import { Modal } from '@/components/common/Modal'
import { PhoneInput } from '@/components/common/PhoneInput'
import { ownersApi } from '@/api/owners'
import { usersApi } from '@/api/users'
import AddressAutocomplete from '@/components/common/AddressAutocomplete'
import CommuneAutocomplete from '@/components/common/CommuneAutocomplete'
import type { Owner } from '@/types/owner'
import type { User } from '@/types/auth'
import { getErrorMessage } from '@/utils/errors'

const schema = z.object({
  civility: z.enum(['M', 'Mme', 'Autre']).optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  company_name: z.string().optional(),
  national_id: z.string().optional(),
  email: z.string().email('Email invalide').optional().or(z.literal('')),
  phone: z.string().optional(),
  address: z.string().optional(),
  zip_code: z.string().optional(),
  city: z.string().optional(),
  country: z.string().optional(),
  iban: z.string().optional(),
  bic: z.string().optional(),
  bank_holder: z.string().optional(),
  notes: z.string().optional(),
  user_id: z.string().uuid().optional().or(z.literal('')),
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
  // ── Accès espace propriétaire (compte de connexion, optionnel) ──────────────
  const [proprioUsers, setProprioUsers] = useState<User[]>([])
  const [showCreateUser, setShowCreateUser] = useState(false)
  const [newUserPassword, setNewUserPassword] = useState('')
  const [creatingUser, setCreatingUser] = useState(false)
  const [createUserError, setCreateUserError] = useState<string | null>(null)

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
      zip_code: owner.zip_code ?? '',
      city: owner.city ?? '',
      country: owner.country ?? '',
      iban: owner.iban ?? '',
      bic: owner.bic ?? '',
      bank_holder: owner.bank_holder ?? '',
      notes: owner.notes ?? '',
      user_id: owner.user_id ?? '',
    } : {},
  })

  const selectedUserId = watch('user_id')
  const firstNameValue = watch('first_name')
  const lastNameValue = watch('last_name')
  const companyValue = watch('company_name')
  const emailValue = watch('email')

  // Comptes « propriétaire » disponibles. En création : seulement ceux non encore
  // rattachés à une fiche. En édition : tous, pour garder le compte lié visible.
  useEffect(() => {
    usersApi.list({ role: 'proprietaire', unlinked_owner: !isEdit })
      .then(r => setProprioUsers(r.data))
      .catch(() => {})
  }, [isEdit])

  const handleCreateUser = async () => {
    const name = (companyValue?.trim() || `${firstNameValue ?? ''} ${lastNameValue ?? ''}`.trim())
    const email = emailValue?.trim()
    if (!name || !email || !newUserPassword.trim()) {
      setCreateUserError('Remplissez le nom/société, l\'email et le mot de passe ci-dessus')
      return
    }
    if (newUserPassword.trim().length < 8) {
      setCreateUserError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }
    setCreatingUser(true)
    setCreateUserError(null)
    try {
      const { data: newUser } = await usersApi.create({
        full_name: name,
        email,
        password: newUserPassword,
        role: 'proprietaire',
      })
      setProprioUsers(prev => [...prev, newUser])
      setValue('user_id', newUser.id)
      setShowCreateUser(false)
      setNewUserPassword('')
    } catch (e: any) {
      setCreateUserError(getErrorMessage(e, 'Erreur lors de la création du compte'))
    } finally {
      setCreatingUser(false)
    }
  }

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
      zip_code: clean(data.zip_code),
      city: clean(data.city),
      country: clean(data.country),
      iban: data.iban ? data.iban.replace(/\s+/g, '').toUpperCase() : null,
      bic: data.bic ? data.bic.replace(/\s+/g, '').toUpperCase() : null,
      bank_holder: clean(data.bank_holder),
      notes: clean(data.notes),
      user_id: clean(data.user_id as string),
    }
    try {
      if (isEdit) {
        await ownersApi.update(owner.id, payload)
      } else {
        await ownersApi.create(payload)
      }
      onSaved()
    } catch (e: any) {
      setSubmitError(getErrorMessage(e, "Erreur lors de l'enregistrement du propriétaire."))
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
        {/* Accès espace propriétaire (compte de connexion, optionnel) */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2 flex items-center gap-1">
            <UserRound size={13} /> Accès espace propriétaire
          </h3>
          {!showCreateUser ? (
            <div className="flex gap-2">
              <select
                value={selectedUserId || ''}
                onChange={e => setValue('user_id', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— Pas encore de compte —</option>
                {proprioUsers.map(u => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setShowCreateUser(true)}
                className="flex items-center gap-1 px-3 py-2 text-xs font-medium text-blue-600 bg-white border border-blue-300 rounded-lg hover:bg-blue-50 transition-colors whitespace-nowrap"
              >
                <Plus size={13} /> Créer
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-blue-700">Créer un compte avec le nom/société et l'email renseignés ci-dessous</span>
                <button type="button" onClick={() => setShowCreateUser(false)} className="text-gray-400 hover:text-gray-600">
                  <X size={14} />
                </button>
              </div>
              {createUserError && <p className="text-xs text-red-600">{createUserError}</p>}
              <input
                value={newUserPassword}
                onChange={e => setNewUserPassword(e.target.value)}
                placeholder="Mot de passe *"
                type="password"
                className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={handleCreateUser}
                disabled={creatingUser}
                className="w-full py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {creatingUser ? 'Création...' : 'Créer le compte propriétaire'}
              </button>
            </div>
          )}
          {selectedUserId && !showCreateUser && (
            <p className="mt-1.5 text-xs text-green-600 flex items-center gap-1">
              <UserRound size={11} /> Compte lié — ce propriétaire peut se connecter à son espace
            </p>
          )}
        </div>

        {/* Identité */}
        <div>
          <SectionTitle icon={Contact}>Identité</SectionTitle>
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
          <SectionTitle icon={Phone}>Contact</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <OwnerField label="Email" name="email" type="email" register={register} errors={errors} />
            <PhoneField label="Téléphone" value={watch('phone') || ''} onChange={v => setValue('phone', v)} />
          </div>
          <div className="mt-3 space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Adresse</label>
              <AddressAutocomplete
                value={watch('address') || ''}
                onChange={v => setValue('address', v)}
                onSelect={({ street, postcode, city }) => {
                  setValue('address', street)
                  if (postcode) setValue('zip_code', postcode)
                  if (city) setValue('city', city)
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="12 rue de la République"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Code postal</label>
                <CommuneAutocomplete
                  value={watch('zip_code') || ''}
                  onChange={v => setValue('zip_code', v)}
                  onSelect={({ zip, city }) => { setValue('zip_code', zip); setValue('city', city) }}
                  display="postcode"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="ex. 75001"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Ville</label>
                <CommuneAutocomplete
                  value={watch('city') || ''}
                  onChange={v => setValue('city', v)}
                  onSelect={({ zip, city }) => { setValue('zip_code', zip); setValue('city', city) }}
                  display="city"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="ex. Paris"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Pays</label>
                <input {...register('country')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="France" />
              </div>
            </div>
          </div>
        </div>

        {/* Coordonnées bancaires */}
        <div>
          <SectionTitle icon={Landmark}>Coordonnées bancaires (RIB)</SectionTitle>
          <p className="-mt-2 text-xs text-gray-400 mb-3">Communiquées au locataire pour le règlement du loyer.</p>
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
