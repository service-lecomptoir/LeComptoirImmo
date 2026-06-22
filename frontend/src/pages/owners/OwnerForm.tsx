import { useState, useEffect } from 'react'
import { useForm, UseFormRegister, FieldErrors } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Contact, Phone, Landmark, UserRound, Plus, X, Percent } from 'lucide-react'
import { Button, Input } from '@/components/ui'
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
import { toast } from '@/store/toast'

const schema = z.object({
  owner_type: z.enum(['person', 'company']),
  // Le <select> civilité a une option vide ('') : on l'accepte (= non renseigné),
  // sinon la validation échoue silencieusement quand la civilité n'est pas choisie.
  civility: z.enum(['M', 'Mme', 'Autre']).or(z.literal('')).optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  company_name: z.string().optional(),
  national_id: z.string().optional(),
  email: z.string().min(1, 'Email requis').email('Email invalide'),
  phone: z.string().min(1, 'Téléphone requis'),
  address: z.string().min(1, 'Adresse requise'),
  zip_code: z.string().min(1, 'Code postal requis'),
  city: z.string().min(1, 'Ville requise'),
  country: z.string().optional(),
  iban: z.string().optional(),
  bic: z.string().optional(),
  bank_holder: z.string().optional(),
  // Surcharge du taux d'honoraires de gestion pour ce mandat (vide = défaut mandataire).
  mgmt_fee_rate: z.string().optional(),
  notes: z.string().optional(),
  user_id: z.string().uuid().optional().or(z.literal('')),
}).superRefine((d, ctx) => {
  // Identité valide selon le type : personne (civilité/prénom/nom) OU société (raison + SIREN/SIRET).
  if (d.owner_type === 'company') {
    if (!d.company_name?.trim()) ctx.addIssue({ code: 'custom', message: 'Société / SCI requise', path: ['company_name'] })
    if (!d.national_id?.trim()) {
      ctx.addIssue({ code: 'custom', message: 'SIREN / SIRET requis', path: ['national_id'] })
    } else {
      const digits = d.national_id.replace(/\D/g, '')
      if (digits.length !== 9 && digits.length !== 14) {
        ctx.addIssue({ code: 'custom', message: 'SIREN (9 chiffres) ou SIRET (14 chiffres)', path: ['national_id'] })
      }
    }
  } else {
    if (!d.first_name?.trim()) ctx.addIssue({ code: 'custom', message: 'Prénom requis', path: ['first_name'] })
    if (!d.last_name?.trim()) ctx.addIssue({ code: 'custom', message: 'Nom requis', path: ['last_name'] })
  }
  // Téléphone : au moins 10 chiffres (national FR ou international).
  if (d.phone?.trim() && d.phone.replace(/\D/g, '').length < 10) {
    ctx.addIssue({ code: 'custom', message: 'Numéro de téléphone incomplet', path: ['phone'] })
  }
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

function PhoneField({ label, value, onChange, required = false, error }: { label: string; value: string; onChange: (v: string) => void; required?: boolean; error?: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <PhoneInput value={value} onChange={onChange} />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
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
  const [creatingUser, setCreatingUser] = useState(false)
  const [createUserError, setCreateUserError] = useState<string | null>(null)

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: owner ? {
      // Société sans prénom de personne => personne morale ; sinon personne physique.
      owner_type: (owner.company_name?.trim() && !owner.first_name?.trim()) ? 'company' : 'person',
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
      mgmt_fee_rate: owner.mgmt_fee_rate != null ? String(owner.mgmt_fee_rate) : '',
      notes: owner.notes ?? '',
      user_id: owner.user_id ?? '',
    } : { owner_type: 'person' },
  })

  const ownerType = watch('owner_type')
  const selectedUserId = watch('user_id')
  const firstNameValue = watch('first_name')
  const lastNameValue = watch('last_name')
  const companyValue = watch('company_name')
  const emailValue = watch('email')

  // Comptes « propriétaire » sélectionnables : ceux non encore rattachés à une
  // fiche. En édition, `owner_id` garde le compte de CETTE fiche visible, tout en
  // excluant les comptes déjà liés à d'AUTRES propriétaires (1 compte = 1 fiche).
  useEffect(() => {
    usersApi.list({ role: 'proprietaire', unlinked_owner: true, owner_id: owner?.id })
      .then(r => setProprioUsers(r.data))
      .catch(() => {})
  }, [owner?.id])

  const handleCreateUser = async () => {
    const name = ownerType === 'company'
      ? (companyValue?.trim() || '')
      : `${firstNameValue ?? ''} ${lastNameValue ?? ''}`.trim()
    const email = emailValue?.trim()
    if (!name || !email) {
      setCreateUserError('Remplissez le nom/société et l\'email ci-dessus')
      return
    }
    setCreatingUser(true)
    setCreateUserError(null)
    try {
      const { data: newUser } = await usersApi.create({
        full_name: name,
        email,
        role: 'proprietaire',
      })
      setProprioUsers(prev => [...prev, newUser])
      setValue('user_id', newUser.id)
      setShowCreateUser(false)
      toast.success(newUser.credentials_email_sent
        ? `Compte créé. Le mot de passe a été généré et envoyé par e-mail à ${email}.`
        : 'Compte créé. Mot de passe généré ; envoyez les identifiants depuis Gestion utilisateurs si l\'e-mail n\'est pas parti.')
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
    const isCompany = data.owner_type === 'company'
    // On ne persiste que l'identité du type choisi. Société : `last_name` recopie la
    // raison sociale (colonne NOT NULL en base, sans incidence d'affichage).
    const payload: any = {
      civility: isCompany ? null : (data.civility || null),
      first_name: isCompany ? null : clean(data.first_name),
      last_name: isCompany ? clean(data.company_name) : clean(data.last_name),
      company_name: isCompany ? clean(data.company_name) : null,
      national_id: isCompany ? clean(data.national_id) : null,
      email: clean(data.email),
      phone: clean(data.phone),
      address: clean(data.address),
      zip_code: clean(data.zip_code),
      city: clean(data.city),
      country: clean(data.country),
      iban: data.iban ? data.iban.replace(/\s+/g, '').toUpperCase() : null,
      bic: data.bic ? data.bic.replace(/\s+/g, '').toUpperCase() : null,
      bank_holder: clean(data.bank_holder),
      mgmt_fee_rate: (data.mgmt_fee_rate ?? '').trim() === ''
        ? null : Number((data.mgmt_fee_rate as string).replace(',', '.')),
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
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={handleSubmit(onSubmit)} disabled={isSubmitting}>
            {isSubmitting ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Créer'}
          </Button>
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
              <p className="text-xs text-gray-500">
                Le mot de passe est généré automatiquement et envoyé par e-mail au propriétaire (changement à la 1re connexion).
              </p>
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
              <UserRound size={11} /> Compte lié : ce propriétaire peut se connecter à son espace
            </p>
          )}
        </div>

        {/* Identité */}
        <div>
          <SectionTitle icon={Contact}>Identité</SectionTitle>
          {/* Type de propriétaire : personne physique ou personne morale (société / SCI).
              Champ enregistré (hidden) pour que setValue alimente bien la validation. */}
          <input type="hidden" {...register('owner_type')} />
          <div className="inline-flex rounded-lg border border-gray-300 p-0.5 mb-3 bg-gray-50">
            {([['person', 'Personne'], ['company', 'Société / SCI']] as const).map(([val, lbl]) => (
              <button
                key={val}
                type="button"
                onClick={() => setValue('owner_type', val, { shouldValidate: false })}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  ownerType === val ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>

          {ownerType === 'company' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <OwnerField label="Raison sociale" name="company_name" placeholder="Raison sociale" required register={register} errors={errors} />
              <OwnerField label="SIREN / SIRET" name="national_id" placeholder="123 456 789" required register={register} errors={errors} />
            </div>
          ) : (
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
              <OwnerField label="Prénom" name="first_name" required register={register} errors={errors} />
              <OwnerField label="Nom" name="last_name" required register={register} errors={errors} />
            </div>
          )}
        </div>

        {/* Contact */}
        <div>
          <SectionTitle icon={Phone}>Contact</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <OwnerField label="Email" name="email" type="email" required register={register} errors={errors} />
            <PhoneField label="Téléphone" required value={watch('phone') || ''} onChange={v => setValue('phone', v, { shouldValidate: true })} error={errors.phone?.message as string} />
          </div>
          <div className="mt-3 space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Adresse<span className="text-red-500 ml-0.5">*</span></label>
              <AddressAutocomplete
                value={watch('address') || ''}
                onChange={v => setValue('address', v, { shouldValidate: true })}
                onSelect={({ street, postcode, city }) => {
                  setValue('address', street, { shouldValidate: true })
                  if (postcode) setValue('zip_code', postcode, { shouldValidate: true })
                  if (city) setValue('city', city, { shouldValidate: true })
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="12 rue de la République"
              />
              {errors.address && <p className="mt-1 text-xs text-red-600">{errors.address.message as string}</p>}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Code postal<span className="text-red-500 ml-0.5">*</span></label>
                <CommuneAutocomplete
                  value={watch('zip_code') || ''}
                  onChange={v => setValue('zip_code', v, { shouldValidate: true })}
                  onSelect={({ zip, city }) => { setValue('zip_code', zip, { shouldValidate: true }); setValue('city', city, { shouldValidate: true }) }}
                  display="postcode"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="ex. 75001"
                />
                {errors.zip_code && <p className="mt-1 text-xs text-red-600">{errors.zip_code.message as string}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Ville<span className="text-red-500 ml-0.5">*</span></label>
                <CommuneAutocomplete
                  value={watch('city') || ''}
                  onChange={v => setValue('city', v, { shouldValidate: true })}
                  onSelect={({ zip, city }) => { setValue('zip_code', zip, { shouldValidate: true }); setValue('city', city, { shouldValidate: true }) }}
                  display="city"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="ex. Paris"
                />
                {errors.city && <p className="mt-1 text-xs text-red-600">{errors.city.message as string}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Pays</label>
                <Input {...register('country')} placeholder="France" />
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

        {/* Mandat de gestion : surcharge du taux d'honoraires */}
        <div>
          <SectionTitle icon={Percent}>Mandat de gestion</SectionTitle>
          <p className="-mt-2 text-xs text-gray-400 mb-3">Laissez vide pour appliquer votre taux d'honoraires par défaut.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <OwnerField label="Taux d'honoraires (%)" name="mgmt_fee_rate" type="number" placeholder="Ex. 8" register={register} errors={errors} />
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
