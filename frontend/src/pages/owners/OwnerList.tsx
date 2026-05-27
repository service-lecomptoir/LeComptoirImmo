import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Building2, Mail, Phone, ShieldCheck } from 'lucide-react'
import { ownersApi } from '@/api/owners'
import { OwnerForm } from './OwnerForm'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import type { OwnerListItem } from '@/types/owner'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

export default function OwnerList() {
  const navigate = useNavigate()
  const [owners, setOwners] = useState<OwnerListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

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

  const initials = (o: OwnerListItem) =>
    (o.company_name || o.full_name || '?').trim().slice(0, 2).toUpperCase()

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Propriétaires</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} propriétaire{total > 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} /> Nouveau propriétaire
        </button>
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

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-gray-500 text-sm">Chargement...</div>
        ) : owners.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-500">
            <Building2 size={32} className="text-gray-300 mb-2" />
            <p className="text-sm">{search ? 'Aucun résultat' : 'Aucun propriétaire enregistré'}</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Nom</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Contact</th>
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
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-orange-700 text-sm font-semibold">{initials(owner)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{owner.full_name}</span>
                        {owner.user_id && (
                          <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded-full" title="Compte propriétaire lié">
                            <ShieldCheck size={10} /> Compte
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5 text-gray-600">
                      {owner.email && <span className="flex items-center gap-1.5"><Mail size={12} />{owner.email}</span>}
                      {owner.phone && <span className="flex items-center gap-1.5"><Phone size={12} />{owner.phone}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {format(new Date(owner.created_at), 'd MMM yyyy', { locale: fr })}
                  </td>
                  <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => setDeleteId(owner.id)}
                      className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50 transition-colors"
                    >
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      {showForm && (
        <OwnerForm
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); fetchOwners(search) }}
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
