import { useEffect, useState, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Users, Plus, Pencil, Trash2, ShieldCheck, CheckCircle, XCircle,
} from 'lucide-react'
import { apiClient } from '@/api/client'
import { tenantsApi } from '@/api/tenants'
import { ownersApi } from '@/api/owners'
import { Modal } from '@/components/common/Modal'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { User, Role } from '@/types/auth'
import { useAuthStore } from '@/store/authStore'

/** Fiche (locataire ou propriétaire) candidate au rattachement d'un compte. */
interface FicheOption {
  id: string
  full_name: string
  email: string | null
  user_id: string | null
}
const NEW_FICHE = '__new__'

// ── Schemas ───────────────────────────────────────────────────────────────────

const createUserSchema = z.object({
  full_name: z.string().min(2, 'Nom requis (min 2 caractères)'),
  email: z.string().email('Email invalide'),
  password: z.string().min(8, 'Mot de passe min 8 caractères'),
  role: z.enum(['locataire', 'proprietaire', 'gestionnaire', 'gestionnaire_proprio', 'admin', 'lecture', 'comptable']),
})

const editUserSchema = z.object({
  full_name: z.string().min(2, 'Nom requis'),
  email: z.string().email('Email invalide'),
  is_active: z.boolean(),
  role: z.enum(['locataire', 'proprietaire', 'gestionnaire', 'gestionnaire_proprio', 'admin', 'lecture', 'comptable']),
})

type CreateUserForm = z.infer<typeof createUserSchema>
type EditUserForm = z.infer<typeof editUserSchema>

// ── Helpers ───────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<Role, string> = {
  locataire: 'Locataire',
  proprietaire: 'Propriétaire',
  gestionnaire: 'Gestionnaire mandataire',
  gestionnaire_proprio: 'Gestionnaire-Propriétaire',
  admin: 'Administrateur',
  lecture: 'Lecture seule',
  comptable: 'Comptable',
}

const ROLE_COLORS: Record<Role, string> = {
  locataire: 'bg-teal-100 text-teal-700',
  proprietaire: 'bg-orange-100 text-orange-700',
  gestionnaire: 'bg-purple-100 text-purple-700',
  gestionnaire_proprio: 'bg-indigo-100 text-indigo-700',
  admin: 'bg-red-100 text-red-700',
  lecture: 'bg-gray-100 text-gray-600',
  comptable: 'bg-blue-100 text-blue-700',
}

function formatDate(iso: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(iso))
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function fetchUsers(): Promise<User[]> {
  const { data } = await apiClient.get<User[]>('/users')
  return data
}

// ── Component ─────────────────────────────────────────────────────────────────

// Rôles disponibles selon le rôle de l'utilisateur connecté
function getCreatableRoles(myRole: Role | undefined): [Role, string][] {
  if (myRole === 'gestionnaire_proprio') {
    return [['locataire', 'Locataire']]
  }
  if (myRole === 'gestionnaire') {
    return [['locataire', 'Locataire'], ['proprietaire', 'Propriétaire']]
  }
  return Object.entries(ROLE_LABELS) as [Role, string][]
}

export default function AdminUsers() {
  const { user: me } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modals state
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<User | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Rattachement d'une fiche (locataire / propriétaire) au nouveau compte
  const [fiches, setFiches] = useState<FicheOption[]>([])
  const [linkFicheId, setLinkFicheId] = useState<string>('')
  // Réinitialisation du mot de passe (édition)
  const [resetPwd, setResetPwd] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setUsers(await fetchUsers())
    } catch {
      setError('Impossible de charger les utilisateurs.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── Create form ──
  const createForm = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: 'gestionnaire' },
  })

  const watchedRole = createForm.watch('role')
  const needsFiche = watchedRole === 'locataire' || watchedRole === 'proprietaire'

  // Charge les fiches (sans compte) à rattacher, selon le rôle choisi.
  useEffect(() => {
    if (!showCreate || !needsFiche) { setFiches([]); return }
    let cancelled = false
    const loader = watchedRole === 'locataire' ? tenantsApi.list({ limit: 200 }) : ownersApi.list({ limit: 200 })
    loader
      .then(r => {
        if (cancelled) return
        const items = (r.data.items ?? []) as FicheOption[]
        setFiches(items.filter(f => !f.user_id))
      })
      .catch(() => { if (!cancelled) setFiches([]) })
    return () => { cancelled = true }
  }, [showCreate, watchedRole, needsFiche])

  const handleCreate = async (values: CreateUserForm) => {
    setSubmitting(true)
    setFormError(null)
    try {
      const isLoc = values.role === 'locataire'
      const isProp = values.role === 'proprietaire'
      if ((isLoc || isProp) && !linkFicheId) {
        setFormError(`Choisissez une fiche ${isLoc ? 'locataire' : 'propriétaire'} à rattacher, ou créez-en une.`)
        setSubmitting(false)
        return
      }

      // 1) Créer le compte utilisateur
      const { data: newUser } = await apiClient.post<User>('/users', values)

      // 2) Rattacher / créer la fiche correspondante
      if (isLoc) {
        if (linkFicheId === NEW_FICHE) {
          const [first, ...rest] = values.full_name.trim().split(/\s+/)
          await apiClient.post('/tenants', {
            first_name: first, last_name: rest.join(' ') || first,
            email: values.email, user_id: newUser.id,
          })
        } else {
          await apiClient.put(`/tenants/${linkFicheId}`, { user_id: newUser.id })
        }
      } else if (isProp) {
        if (linkFicheId === NEW_FICHE) {
          await apiClient.post('/owners', {
            last_name: values.full_name.trim(), email: values.email, user_id: newUser.id,
          })
        } else {
          await apiClient.put(`/owners/${linkFicheId}`, { user_id: newUser.id })
        }
      }

      await load()
      setShowCreate(false)
      createForm.reset()
      setLinkFicheId('')
    } catch (e: any) {
      setFormError(e?.response?.data?.detail || 'Erreur lors de la création.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Edit form ──
  const editForm = useForm<EditUserForm>({
    resolver: zodResolver(editUserSchema),
  })

  const openEdit = (u: User) => {
    setEditTarget(u)
    editForm.reset({
      full_name: u.full_name, email: u.email, is_active: u.is_active, role: u.role,
    })
    setResetPwd('')
    setFormError(null)
  }

  const handleEdit = async (values: EditUserForm) => {
    if (!editTarget) return
    setSubmitting(true)
    setFormError(null)
    try {
      // Coordonnées + RIB du propriétaire = sur la fiche (onglet Propriétaires),
      // plus sur le compte : ici on ne touche qu'aux infos de compte.
      await apiClient.put(`/users/${editTarget.id}`, {
        full_name: values.full_name,
        email: values.email,
        is_active: values.is_active,
      })
      // Update role if changed
      if (values.role !== editTarget.role) {
        await apiClient.patch(`/users/${editTarget.id}/role`, { role: values.role })
      }
      // Réinitialisation du mot de passe (optionnel)
      if (resetPwd.trim()) {
        if (resetPwd.trim().length < 8) {
          setFormError('Le nouveau mot de passe doit contenir au moins 8 caractères.')
          setSubmitting(false)
          return
        }
        await apiClient.patch(`/users/${editTarget.id}/password`, { new_password: resetPwd.trim() })
      }
      await load()
      setEditTarget(null)
      setResetPwd('')
    } catch (e: any) {
      setFormError(e?.response?.data?.detail || 'Erreur lors de la modification.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Delete ──
  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await apiClient.delete(`/users/${deleteTarget.id}`)
      await load()
      setDeleteTarget(null)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erreur lors de la suppression.')
    }
  }

  // ── Render ──
  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div className="flex items-center gap-3">
          <ShieldCheck size={24} className="text-gray-700" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Administration</h1>
            <p className="text-sm text-gray-500">Gestion des utilisateurs</p>
          </div>
        </div>
        <button
          onClick={() => {
            const defaultRole = me?.role === 'gestionnaire_proprio' ? 'locataire' : 'gestionnaire'
            setShowCreate(true); setFormError(null); setLinkFicheId(''); createForm.reset({ role: defaultRole as Role })
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <Plus size={16} />
          Nouvel utilisateur
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="divide-y divide-gray-100">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 animate-pulse bg-gray-50" />
            ))}
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <Users size={48} className="mx-auto mb-3 opacity-40" />
            <p className="text-lg font-medium">Aucun utilisateur</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Nom</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Email</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Rôle</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Statut</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Créé le</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                        <span className="text-blue-700 text-xs font-semibold">
                          {u.full_name?.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <span className="font-medium text-gray-900">{u.full_name}</span>
                      {u.id === me?.id && (
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                          Moi
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[u.role]}`}>
                      {ROLE_LABELS[u.role]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {u.is_active ? (
                        <><CheckCircle size={11} /> Actif</>
                      ) : (
                        <><XCircle size={11} /> Inactif</>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => openEdit(u)}
                        className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Modifier"
                      >
                        <Pencil size={14} />
                      </button>
                      {u.id !== me?.id && (
                        <button
                          onClick={() => setDeleteTarget(u)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Supprimer"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {/* ── Create Modal ── */}
      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nouvel utilisateur"
        size="md"
      >
        <form onSubmit={createForm.handleSubmit(handleCreate)} className="space-y-4">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom complet *</label>
            <input
              {...createForm.register('full_name')}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Jean Dupont"
            />
            {createForm.formState.errors.full_name && (
              <p className="text-red-500 text-xs mt-1">{createForm.formState.errors.full_name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              {...createForm.register('email')}
              type="email"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="jean@example.com"
            />
            {createForm.formState.errors.email && (
              <p className="text-red-500 text-xs mt-1">{createForm.formState.errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mot de passe *</label>
            <input
              {...createForm.register('password')}
              type="password"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Min. 8 caractères"
            />
            {createForm.formState.errors.password && (
              <p className="text-red-500 text-xs mt-1">{createForm.formState.errors.password.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rôle *</label>
            <select
              {...createForm.register('role', { onChange: () => setLinkFicheId('') })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {getCreatableRoles(me?.role).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          {/* Rattachement à une fiche locataire / propriétaire */}
          {needsFiche && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-1.5">
              <label className="block text-sm font-medium text-blue-800">
                Fiche {watchedRole === 'locataire' ? 'locataire' : 'propriétaire'} à rattacher *
              </label>
              <p className="text-xs text-blue-700/80">
                Ce compte donnera accès à l'espace en ligne de cette fiche. Choisissez une fiche
                existante, ou créez-en une à partir du nom et de l'email saisis ci-dessus.
              </p>
              <select
                value={linkFicheId}
                onChange={e => setLinkFicheId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— Choisir une fiche —</option>
                {fiches.map(f => (
                  <option key={f.id} value={f.id}>
                    {f.full_name}{f.email ? ` (${f.email})` : ''}
                  </option>
                ))}
                <option value={NEW_FICHE}>➕ Créer une nouvelle fiche (depuis le nom / email)</option>
              </select>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {submitting ? 'Création…' : 'Créer'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Edit Modal ── */}
      <Modal
        isOpen={!!editTarget}
        onClose={() => setEditTarget(null)}
        title={`Modifier — ${editTarget?.full_name}`}
        size="md"
      >
        <form onSubmit={editForm.handleSubmit(handleEdit)} className="space-y-4">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom complet *</label>
            <input
              {...editForm.register('full_name')}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {editForm.formState.errors.full_name && (
              <p className="text-red-500 text-xs mt-1">{editForm.formState.errors.full_name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              {...editForm.register('email')}
              type="email"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {editForm.formState.errors.email && (
              <p className="text-red-500 text-xs mt-1">{editForm.formState.errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rôle *</label>
            <select
              {...editForm.register('role')}
              disabled={editTarget?.id === me?.id || me?.role === 'gestionnaire_proprio'}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            >
              {getCreatableRoles(me?.role).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            {editTarget?.id === me?.id && (
              <p className="text-xs text-gray-400 mt-1">Vous ne pouvez pas modifier votre propre rôle.</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              {...editForm.register('is_active')}
              disabled={editTarget?.id === me?.id}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <label htmlFor="is_active" className="text-sm text-gray-700">
              Compte actif
            </label>
          </div>

          {/* Coordonnées + RIB du propriétaire : gérés sur la fiche (onglet Propriétaires). */}
          {(editForm.watch('role') === 'proprietaire' || editForm.watch('role') === 'gestionnaire_proprio') && (
            <div className="px-3 py-2 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700">
              Les coordonnées et le RIB du propriétaire se renseignent sur sa fiche, dans l'onglet
              <span className="font-semibold"> Propriétaires</span>.
            </div>
          )}

          {/* Réinitialiser le mot de passe */}
          <div className="pt-3 border-t border-gray-100">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Réinitialiser le mot de passe
            </label>
            <input
              type="text"
              value={resetPwd}
              onChange={e => setResetPwd(e.target.value)}
              autoComplete="new-password"
              placeholder="Laisser vide pour ne pas changer"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              Définit un nouveau mot de passe pour cet utilisateur (min. 8 caractères). Communiquez-le-lui ;
              il pourra le changer ensuite depuis son espace.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setEditTarget(null)}
              className="px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {submitting ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Delete Confirm ── */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Supprimer l'utilisateur"
        message={`Voulez-vous vraiment supprimer l'utilisateur "${deleteTarget?.full_name}" ? Cette action est irréversible.`}
        confirmLabel="Supprimer"
        confirmVariant="red"
      />
    </div>
  )
}
