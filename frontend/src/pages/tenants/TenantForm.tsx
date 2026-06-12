import { useEffect, useState } from 'react'
import { useForm, UseFormRegister, FieldErrors } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { UserRound, Plus, X, Contact, Phone, Briefcase, FileText } from 'lucide-react'
import { Modal } from '@/components/common/Modal'
import { SectionTitle } from '@/components/common/SectionTitle'
import { PhoneInput } from '@/components/common/PhoneInput'
import { formatNir, digitsOnly } from '@/utils/format'
import { getErrorMessage } from '@/utils/errors'
import { tenantsApi } from '@/api/tenants'
import { usersApi } from '@/api/users'
import type { Tenant } from '@/types/tenant'
import type { User } from '@/types/auth'

const schema = z.object({
  tenant_type: z.enum(['person', 'company']),
  civility: z.enum(['M', 'Mme', 'Autre']).optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  company_name: z.string().optional(),
  siret: z.string().optional(),
  email: z.string().min(1, 'Email requis').email('Email invalide'),
  phone: z.string().optional(),
  birth_date: z.string().optional(),
  birth_place: z.string().optional(),
  national_id: z.string().optional(),
  employer: z.string().optional(),
  employer_phone: z.string().optional(),
  monthly_income: z.number().positive().optional().or(z.literal('')),
  income_source: z.string().optional(),
  notes: z.string().optional(),
  user_id: z.string().uuid().optional().or(z.literal('')),
}).superRefine((d, ctx) => {
  if (d.tenant_type === 'company') {
    if (!d.company_name?.trim()) ctx.addIssue({ code: 'custom', message: 'Société / SCI requise', path: ['company_name'] })
    if (!d.siret?.trim()) ctx.addIssue({ code: 'custom', message: 'SIREN / SIRET requis', path: ['siret'] })
  } else {
    if (!d.first_name?.trim()) ctx.addIssue({ code: 'custom', message: 'Prénom requis', path: ['first_name'] })
    if (!d.last_name?.trim()) ctx.addIssue({ code: 'custom', message: 'Nom requis', path: ['last_name'] })
    if (!d.birth_date?.trim()) ctx.addIssue({ code: 'custom', message: 'Date de naissance requise', path: ['birth_date'] })
    if (!d.national_id?.trim()) ctx.addIssue({ code: 'custom', message: 'Numéro de sécurité sociale requis', path: ['national_id'] })
  }
})

type FormData = z.infer<typeof schema>

// Sources de revenus courantes (champ informatif — stocké en texte côté API).
const INCOME_SOURCES = [
  'Salaire (CDI)',
  'Salaire (CDD)',
  'Intérim',
  'Indépendant / profession libérale',
  'Chef d’entreprise / dirigeant',
  'Retraite',
  'Pension / rente',
  'Allocations (CAF, chômage…)',
  'Revenus fonciers',
  'Bourse étudiante',
  'Garant / caution solidaire',
  'Autre',
] as const

// ─── Field helper — must be defined at module level (outside TenantForm)
// so React never treats it as a new component type on re-render, which would
// cause inputs to lose focus every time state changes.
interface FieldProps {
  label: string
  name: keyof FormData
  type?: string
  required?: boolean
  register: UseFormRegister<FormData>
  errors: FieldErrors<FormData>
}
function TenantField({ label, name, type = 'text', required = false, register, errors }: FieldProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        {...register(name)}
        type={type}
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
  tenant?: Tenant
  onClose: () => void
  onSaved: () => void
}

export function TenantForm({ tenant, onClose, onSaved }: Props) {
  const isEdit = !!tenant
  const [locataireUsers, setLocataireUsers] = useState<User[]>([])
  const [showCreateUser, setShowCreateUser] = useState(false)
  const [newUserPassword, setNewUserPassword] = useState('')
  const [creatingUser, setCreatingUser] = useState(false)
  const [createUserError, setCreateUserError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: tenant ? {
      tenant_type: (tenant.company_name?.trim() && !tenant.first_name?.trim()) ? 'company' : 'person',
      civility: tenant.civility ?? undefined,
      first_name: tenant.first_name,
      last_name: tenant.last_name,
      company_name: tenant.company_name ?? '',
      siret: tenant.siret ?? '',
      email: tenant.email ?? '',
      phone: tenant.phone ?? '',
      birth_date: tenant.birth_date ?? '',
      birth_place: tenant.birth_place ?? '',
      national_id: tenant.national_id ?? '',
      employer: tenant.employer ?? '',
      employer_phone: tenant.employer_phone ?? '',
      notes: tenant.notes ?? '',
      user_id: tenant.user_id ?? '',
    } : { tenant_type: 'person' },
  })

  const tenantType = watch('tenant_type')
  const selectedUserId = watch('user_id')
  const emailValue = watch('email')
  const firstNameValue = watch('first_name')
  const lastNameValue = watch('last_name')
  const companyValue = watch('company_name')

  useEffect(() => {
    // En création : on masque les comptes déjà liés à un locataire.
    // En édition : on garde tout pour que le compte déjà lié à CE locataire reste affiché.
    usersApi.list({ role: 'locataire', unlinked_tenant: !isEdit })
      .then(r => setLocataireUsers(r.data))
      .catch(() => {})
  }, [isEdit])

  const handleCreateUser = async () => {
    const name = tenantType === 'company'
      ? (companyValue?.trim() || '')
      : `${firstNameValue ?? ''} ${lastNameValue ?? ''}`.trim()
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
        role: 'locataire',
      })
      setLocataireUsers(prev => [...prev, newUser])
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
    // Champ vidé → on envoie `null` (et non `undefined`) : undefined est omis du JSON
    // par axios → côté API (exclude_unset) le champ n'est pas mis à jour, donc l'ancienne
    // valeur persiste. `null` efface explicitement ET évite la 422 d'un "" sur une date/email.
    const clean = (v?: string): string | null => {
      const t = (v ?? '').trim()
      return t === '' ? null : t
    }
    const isCompany = data.tenant_type === 'company'
    // Société : on ne garde que l'identité morale ; first_name vide + last_name = raison
    // sociale (colonnes NOT NULL en base, sans incidence d'affichage). national_id = SIREN/SIRET.
    const payload: any = {
      civility: isCompany ? null : (data.civility || null),
      first_name: isCompany ? '' : (data.first_name || '').trim(),
      last_name: isCompany ? (data.company_name || '').trim() : (data.last_name || '').trim(),
      company_name: isCompany ? clean(data.company_name) : null,
      siret: isCompany ? clean(data.siret) : null,
      birth_date: isCompany ? null : clean(data.birth_date),
      birth_place: isCompany ? null : clean(data.birth_place),
      national_id: isCompany ? null : clean(data.national_id),
      email: clean(data.email),
      phone: clean(data.phone),
      employer: clean(data.employer),
      employer_phone: clean(data.employer_phone),
      monthly_income: data.monthly_income ? Number(data.monthly_income) : null,
      income_source: clean(data.income_source),
      notes: clean(data.notes),
      user_id: clean(data.user_id as string),
    }
    try {
      if (isEdit) {
        await tenantsApi.update(tenant.id, payload)
      } else {
        await tenantsApi.create(payload)
      }
      onSaved()
    } catch (e: any) {
      setSubmitError(getErrorMessage(e, "Erreur lors de l'enregistrement du locataire."))
    }
  }

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? 'Modifier le locataire' : 'Nouveau locataire'}
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
        {/* Compte locataire */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2 flex items-center gap-1">
            <UserRound size={13} /> Accès espace locataire
          </h3>
          {!showCreateUser ? (
            <div className="flex gap-2">
              <select
                value={selectedUserId || ''}
                onChange={e => setValue('user_id', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— Pas encore de compte —</option>
                {locataireUsers.map(u => (
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
                <span className="text-xs font-medium text-blue-700">Créer un compte avec le prénom/nom/email renseignés ci-dessous</span>
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
                {creatingUser ? 'Création...' : 'Créer le compte locataire'}
              </button>
            </div>
          )}
          {selectedUserId && !showCreateUser && (
            <p className="mt-1.5 text-xs text-green-600 flex items-center gap-1">
              <UserRound size={11} /> Compte lié : ce locataire peut se connecter à son espace
            </p>
          )}
        </div>

        {/* Identité */}
        <div>
          <SectionTitle icon={Contact}>Identité</SectionTitle>
          {/* Type de locataire : personne physique ou personne morale (société / SCI) */}
          <div className="inline-flex rounded-lg border border-gray-300 p-0.5 mb-3 bg-gray-50">
            {([['person', 'Personne'], ['company', 'Société / SCI']] as const).map(([val, lbl]) => (
              <button
                key={val}
                type="button"
                onClick={() => setValue('tenant_type', val, { shouldValidate: false })}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  tenantType === val ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>

          {tenantType === 'company' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <TenantField label="Société / SCI" name="company_name" required register={register} errors={errors} />
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  SIREN / SIRET<span className="text-red-500 ml-0.5">*</span>
                </label>
                <input
                  {...register('siret')}
                  placeholder="123 456 789 00012"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.siret && <p className="mt-1 text-xs text-red-600">{errors.siret.message as string}</p>}
              </div>
            </div>
          ) : (
            <>
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
                <TenantField label="Prénom" name="first_name" required register={register} errors={errors} />
                <TenantField label="Nom" name="last_name" required register={register} errors={errors} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
                <TenantField label="Date de naissance" name="birth_date" type="date" required register={register} errors={errors} />
                <TenantField label="Lieu de naissance" name="birth_place" register={register} errors={errors} />
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Numéro de sécurité sociale<span className="text-red-500 ml-0.5">*</span>
                  </label>
                  <input
                    value={formatNir(watch('national_id') || '')}
                    onChange={e => setValue('national_id', digitsOnly(e.target.value), { shouldValidate: true })}
                    inputMode="numeric"
                    placeholder="1 99 11 33 123 456 78"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.national_id && <p className="mt-1 text-xs text-red-600">{errors.national_id.message as string}</p>}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Contact */}
        <div>
          <SectionTitle icon={Phone}>Contact</SectionTitle>
          <div className="space-y-3">
            {/* Email en pleine largeur : une adresse longue reste entièrement visible */}
            <TenantField label="Email" name="email" type="email" required register={register} errors={errors} />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <PhoneField label="Téléphone" value={watch('phone') || ''} onChange={v => setValue('phone', v)} />
            </div>
          </div>
        </div>

        {/* Situation professionnelle */}
        <div>
          <SectionTitle icon={Briefcase}>Situation professionnelle</SectionTitle>
          <div className="space-y-3">
            <TenantField label="Employeur" name="employer" register={register} errors={errors} />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <PhoneField label="Tél. employeur" value={watch('employer_phone') || ''} onChange={v => setValue('employer_phone', v)} />
              <TenantField label="Revenu mensuel (€)" name="monthly_income" type="number" register={register} errors={errors} />
            </div>
          </div>
          <div className="mt-3">
            <label className="block text-xs font-medium text-gray-700 mb-1">Source de revenus</label>
            <select
              {...register('income_source')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— Sélectionner —</option>
              {INCOME_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Notes */}
        <div>
          <SectionTitle icon={FileText}>Notes</SectionTitle>
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
