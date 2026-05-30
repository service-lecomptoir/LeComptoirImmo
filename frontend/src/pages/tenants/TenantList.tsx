import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, UserRound, ShieldCheck, Pencil, Trash2, Mail, Phone } from 'lucide-react'
import { tenantsApi } from '@/api/tenants'
import { TenantForm } from './TenantForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { Tenant, TenantListItem } from '@/types/tenant'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { useAuthStore } from '@/store/authStore'
import { ViewToggle } from '@/components/common/ViewToggle'
import { useViewMode } from '@/hooks/useViewMode'

export default function TenantList() {
  const navigate = useNavigate()
  const [tenants, setTenants] = useState<TenantListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editTenant, setEditTenant] = useState<Tenant | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const user = useAuthStore(s => s.user)
  const canToggleView = ['gestionnaire', 'gestionnaire_proprio', 'proprietaire'].includes(user?.role ?? '')
  const [view, setView] = useViewMode('tenants', 'list')

  const fetchTenants = useCallback(async (q: string) => {
    setIsLoading(true)
    try {
      const { data } = await tenantsApi.list({ search: q || undefined, limit: 100 })
      setTenants(data.items)
      setTotal(data.total)
    } catch (e) {
      console.error(e)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchTenants(search), 300)
    return () => clearTimeout(t)
  }, [search, fetchTenants])

  const openEdit = async (id: string) => {
    try {
      const { data } = await tenantsApi.get(id)
      setEditTenant(data)
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await tenantsApi.delete(deleteId)
      setDeleteId(null)
      fetchTenants(search)
    } catch (e: any) {
      setDeleteError(
        e?.response?.data?.detail ||
        "La suppression a échoué. Ce locataire est peut-être rattaché à un contrat."
      )
    } finally {
      setIsDeleting(false)
    }
  }

  const closeDelete = () => { setDeleteId(null); setDeleteError(null) }

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Locataires</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} locataire{total > 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          {canToggleView && <ViewToggle value={view} onChange={setView} />}
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus size={16} /> Nouveau locataire
          </button>
        </div>
      </div>

      {/* Recherche */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher par nom, email, téléphone..."
          className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Liste ou mosaïque */}
      {isLoading ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-sm">Chargement...</div>
      ) : tenants.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500 bg-white rounded-xl border border-gray-200 shadow-sm">
          <UserRound size={32} className="text-gray-300 mb-2" />
          <p className="text-sm">{search ? 'Aucun résultat' : 'Aucun locataire enregistré'}</p>
        </div>
      ) : view === 'list' ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Nom</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Ajouté le</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tenants.map(tenant => (
                  <tr
                    key={tenant.id}
                    onClick={() => navigate(`/tenants/${tenant.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{tenant.full_name}</span>
                        {tenant.user_id && (
                          <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full" title="Compte locataire lié">
                            <ShieldCheck size={10} /> Compte
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {format(new Date(tenant.created_at), 'd MMM yyyy', { locale: fr })}
                    </td>
                    <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(tenant.id)}
                          className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 transition-colors"
                          title="Modifier"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setDeleteId(tenant.id)}
                          className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors"
                          title="Supprimer"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {tenants.map(tenant => (
            <div
              key={tenant.id}
              onClick={() => navigate(`/tenants/${tenant.id}`)}
              className="group relative flex flex-col gap-3 bg-white rounded-xl border border-gray-200 shadow-sm p-4 cursor-pointer transition-all hover:shadow-md hover:border-blue-300"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <UserRound size={18} className="text-blue-700" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900 truncate">{tenant.full_name}</p>
                    {tenant.user_id && (
                      <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full shrink-0" title="Compte locataire lié">
                        <ShieldCheck size={10} /> Compte
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {(tenant.email || tenant.phone) && (
                <div className="flex flex-col gap-1 text-xs text-gray-600">
                  {tenant.email && <span className="flex items-center gap-1.5 truncate"><Mail size={12} className="text-gray-400 shrink-0" />{tenant.email}</span>}
                  {tenant.phone && <span className="flex items-center gap-1.5"><Phone size={12} className="text-gray-400 shrink-0" />{tenant.phone}</span>}
                </div>
              )}

              <div className="mt-auto flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
                <span className="text-xs text-gray-400">{format(new Date(tenant.created_at), 'd MMM yyyy', { locale: fr })}</span>
                <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                  <button
                    onClick={() => openEdit(tenant.id)}
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 transition-colors"
                    title="Modifier"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => setDeleteId(tenant.id)}
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors"
                    title="Supprimer"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {showForm && (
        <TenantForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchTenants(search) }}
        />
      )}
      {editTenant && (
        <TenantForm
          tenant={editTenant}
          onClose={() => setEditTenant(null)}
          onSaved={() => { setEditTenant(null); fetchTenants(search) }}
        />
      )}
      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={closeDelete}
        onConfirm={handleDelete}
        title="Supprimer le locataire"
        message={deleteError
          ? `⚠️ ${deleteError}`
          : "Cette action est irréversible. Êtes-vous sûr de vouloir supprimer ce locataire ?"}
        confirmLabel={deleteError ? 'Réessayer' : 'Supprimer'}
        isLoading={isDeleting}
      />
    </div>
  )
}
