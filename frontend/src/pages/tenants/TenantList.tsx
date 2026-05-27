import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, UserRound, ShieldCheck, Pencil, Trash2 } from 'lucide-react'
import { tenantsApi } from '@/api/tenants'
import { TenantForm } from './TenantForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { Tenant, TenantListItem } from '@/types/tenant'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

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
    try {
      await tenantsApi.delete(deleteId)
      setDeleteId(null)
      fetchTenants(search)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Locataires</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} locataire{total > 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} /> Nouveau locataire
        </button>
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

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-gray-500 text-sm">Chargement...</div>
        ) : tenants.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-500">
            <UserRound size={32} className="text-gray-300 mb-2" />
            <p className="text-sm">{search ? 'Aucun résultat' : 'Aucun locataire enregistré'}</p>
          </div>
        ) : (
          <table className="w-full text-sm">
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
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-blue-700 text-sm font-semibold">
                          {tenant.first_name.charAt(0)}{tenant.last_name.charAt(0)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{tenant.full_name}</span>
                        {tenant.user_id && (
                          <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full" title="Compte locataire lié">
                            <ShieldCheck size={10} /> Compte
                          </span>
                        )}
                      </div>
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
        )}
      </div>

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
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Supprimer le locataire"
        message="Cette action est irréversible. Êtes-vous sûr de vouloir supprimer ce locataire ?"
        isLoading={isDeleting}
      />
    </div>
  )
}
