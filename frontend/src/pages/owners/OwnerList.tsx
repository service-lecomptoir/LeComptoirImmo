import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Building2, ShieldCheck, Pencil, Trash2, Mail, Phone } from 'lucide-react'
import { ownersApi } from '@/api/owners'
import { OwnerForm } from './OwnerForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { Owner, OwnerListItem } from '@/types/owner'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { useAuthStore } from '@/store/authStore'
import { ViewToggle } from '@/components/common/ViewToggle'
import { useViewMode } from '@/hooks/useViewMode'

export default function OwnerList() {
  const navigate = useNavigate()
  const [owners, setOwners] = useState<OwnerListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editOwner, setEditOwner] = useState<Owner | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const user = useAuthStore(s => s.user)
  const isManager = user?.role === 'gestionnaire' || user?.role === 'gestionnaire_proprio'
  const [view, setView] = useViewMode('owners', 'list')

  const fetchOwners = useCallback(async (q: string) => {
    setIsLoading(true)
    try {
      const { data } = await ownersApi.list({ search: q || undefined, limit: 100 })
      setOwners(data.items)
      setTotal(data.total)
    } catch (e) {
      console.error(e)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchOwners(search), 300)
    return () => clearTimeout(t)
  }, [search, fetchOwners])

  const openEdit = async (id: string) => {
    try {
      const { data } = await ownersApi.get(id)
      setEditOwner(data)
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    setIsDeleting(true)
    try {
      await ownersApi.delete(deleteId)
      setDeleteId(null)
      fetchOwners(search)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Propriétaires</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} propriétaire{total > 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-3">
          {isManager && <ViewToggle value={view} onChange={setView} />}
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus size={16} /> Nouveau propriétaire
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
          placeholder="Rechercher par nom, société, email, téléphone..."
          className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Liste ou mosaïque */}
      {isLoading ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-sm">Chargement...</div>
      ) : owners.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500 bg-white rounded-xl border border-gray-200 shadow-sm">
          <Building2 size={32} className="text-gray-300 mb-2" />
          <p className="text-sm">{search ? 'Aucun résultat' : 'Aucun propriétaire enregistré'}</p>
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
                {owners.map(owner => (
                  <tr
                    key={owner.id}
                    onClick={() => navigate(`/owners/${owner.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{owner.full_name}</span>
                        {owner.user_id && (
                          <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full" title="Compte propriétaire lié">
                            <ShieldCheck size={10} /> Compte
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {format(new Date(owner.created_at), 'd MMM yyyy', { locale: fr })}
                    </td>
                    <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(owner.id)}
                          className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 transition-colors"
                          title="Modifier"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setDeleteId(owner.id)}
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
          {owners.map(owner => (
            <div
              key={owner.id}
              onClick={() => navigate(`/owners/${owner.id}`)}
              className="group relative flex flex-col gap-3 bg-white rounded-xl border border-gray-200 shadow-sm p-4 cursor-pointer transition-all hover:shadow-md hover:border-blue-300"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <span className="text-blue-700 text-sm font-semibold">{owner.full_name.charAt(0).toUpperCase()}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900 truncate">{owner.full_name}</p>
                    {owner.user_id && (
                      <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full shrink-0" title="Compte propriétaire lié">
                        <ShieldCheck size={10} /> Compte
                      </span>
                    )}
                  </div>
                  {owner.company_name && <p className="text-xs text-gray-500 truncate">{owner.company_name}</p>}
                </div>
              </div>

              {(owner.email || owner.phone) && (
                <div className="flex flex-col gap-1 text-xs text-gray-600">
                  {owner.email && <span className="flex items-center gap-1.5 truncate"><Mail size={12} className="text-gray-400 shrink-0" />{owner.email}</span>}
                  {owner.phone && <span className="flex items-center gap-1.5"><Phone size={12} className="text-gray-400 shrink-0" />{owner.phone}</span>}
                </div>
              )}

              <div className="mt-auto flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
                <span className="text-xs text-gray-400">{format(new Date(owner.created_at), 'd MMM yyyy', { locale: fr })}</span>
                <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                  <button
                    onClick={() => openEdit(owner.id)}
                    className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 transition-colors"
                    title="Modifier"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => setDeleteId(owner.id)}
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
        <OwnerForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchOwners(search) }}
        />
      )}
      {editOwner && (
        <OwnerForm
          owner={editOwner}
          onClose={() => setEditOwner(null)}
          onSaved={() => { setEditOwner(null); fetchOwners(search) }}
        />
      )}
      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Supprimer le propriétaire"
        message="Cette action est irréversible. Êtes-vous sûr de vouloir supprimer ce propriétaire ?"
        isLoading={isDeleting}
      />
    </div>
  )
}
