import { useEffect, useState, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Users, Plus, Pencil, Trash2, ShieldCheck, CheckCircle, XCircle,
} from 'lucide-react'
import { apiClient } from '@/api/client'
import { Modal } from '@/components/common/Modal'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { User, Role } from '@/types/auth'
import { useAuthStore } from '@/store/authStore'

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
  iban: z.string().optional(),
  bic: z.string().optional(),
  bank_holder: z.string().optional(),
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

  const handleCreate = async (values: CreateUserForm) => {
    setSubmitting(true)
    setFormError(null)
    try {
      await apiClient.post('/users', values)
      await load()
      setShowCreate(false)
      createForm.reset()
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
      iban: u.iban ?? '', bic: u.bic ?? '', bank_holder: u.bank_holder ?? '',
    })
    setFormError(null)
  }

  const handleEdit = async (values: EditUserForm) => {
    if (!editTarget) return
    setSubmitting(true)
    setFormError(null)
    try {
      // RIB : pertinent uniquement pour les comptes qui encaissent (propriétaire / GP)
      const ribRoles = values.role === 'proprietaire' || values.role === 'gestionnaire_proprio'
      const ribFields = ribRoles ? {
        iban: values.iban ? values.iban.replace(/\s+/g, '').toUpperCase() : null,
        bic: values.bic ? values.bic.replace(/\s+/g, '').toUpperCase() : null,
        bank_holder: values.bank_holder || null,
      } : {}
      // Update basic info (+ RIB le cas échéant)
      await apiClient.put(`/users/${editTarget.id}`, {
        full_name: values.full_name,
        email: values.email,
        is_active: values.is_active,
        ...ribFields,
      })
      // Update role if changed
      if (values.role !== editTarget.role) {
        await apiClient.patch(`/users/${editTarget.id}/role`, { role: values.role })
      }
      await load()
      setEditTarget(null)
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
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
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
            setShowCreate(true); setFormError(null); createForm.reset({ role: defaultRole as Role })
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <Plus size={16} />
          {me?.role === 'gestionnaire_proprio' ? 'Nouveau locataire' : 'Nouvel utilisateur'}
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
          <table className="w-full text-sm">
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
              {...createForm.register('role')}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {getCreatableRoles(me?.role).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

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

          {/* ── RIB du propriétaire (renseigné par le gestionnaire) ── */}
          {(editForm.watch('role') === 'proprietaire' || editForm.watch('role') === 'gestionnaire_proprio') && (
            <div className="pt-3 border-t border-gray-100 space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Coordonnées bancaires (RIB)
              </p>
              <p className="text-xs text-gray-400 -mt-1">
                Communiqué aux locataires de ce propriétaire pour le règlement par virement.
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Titulaire du compte</label>
                <input
                  {...editForm.register('bank_holder')}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Nom figurant sur le compte"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">IBAN</label>
                  <input
                    {...editForm.register('iban')}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="FR76 3000 4028 3798 7654 3210 943"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">BIC</label>
                  <input
                    {...editForm.register('bic')}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="BNPAFRPPXXX"
                  />
                </div>
              </div>
            </div>
          )}

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
