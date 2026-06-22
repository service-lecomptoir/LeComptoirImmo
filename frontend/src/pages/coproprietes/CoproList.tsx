import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Building, Trash2, Pencil } from 'lucide-react'
import { Button } from '@/components/ui'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { CardGridSkeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'
import { canManage } from '@/utils/permissions'
import { coproApi, type CoproListItem, type CoproDetail } from '@/api/coproprietes'
import { CoproForm } from './CoproForm'

export default function CoproList() {
  const navigate = useNavigate()
  const [items, setItems] = useState<CoproListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editCopro, setEditCopro] = useState<CoproDetail | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const user = useAuthStore(s => s.user)
  const canWrite = canManage(user?.role)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await coproApi.list()
      setItems(data)
    } catch (e) {
      console.error(e)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetch() }, [fetch])

  const openEdit = async (id: string) => {
    try {
      const { data } = await coproApi.get(id)
      setEditCopro(data)
    } catch (e) { console.error(e) }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    setDeleting(true)
    try {
      await coproApi.delete(deleteId)
      setDeleteId(null)
      fetch()
      toast.success('Copropriété supprimée')
    } finally { setDeleting(false) }
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Syndic — Copropriétés</h1>
          <p className="text-sm text-gray-500 mt-0.5">{items.length} copropriété{items.length > 1 ? 's' : ''}</p>
        </div>
        {canWrite && (
          <Button onClick={() => setShowForm(true)} leftIcon={<Plus size={16} />}>Nouvelle copropriété</Button>
        )}
      </div>

      {loading && items.length === 0 ? (
        <CardGridSkeleton />
      ) : items.length === 0 ? (
        <EmptyState icon={Building} title="Aucune copropriété" />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(c => (
            <div key={c.id}
              onClick={() => navigate(`/coproprietes/${c.id}`)}
              className="group relative flex flex-col gap-3 bg-white rounded-xl border border-gray-200 shadow-sm p-4 cursor-pointer transition-all hover:shadow-md hover:border-blue-300">
              <div className="flex items-start gap-3">
                <span className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                  <Building size={18} className="text-blue-600" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-gray-900 truncate">{c.name}</p>
                  {c.city && <p className="text-xs text-gray-500 truncate">{c.city}</p>}
                  {c.ref_code && <p className="text-[11px] text-gray-400">{c.ref_code}</p>}
                </div>
              </div>
              <div className="mt-auto flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
                <span className="text-xs text-gray-500">{c.lot_count} lot{c.lot_count > 1 ? 's' : ''}</span>
                {canWrite && (
                  <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                    <button onClick={() => openEdit(c.id)} title="Modifier"
                      className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 transition-colors">
                      <Pencil size={14} />
                    </button>
                    <button onClick={() => setDeleteId(c.id)} title="Supprimer"
                      className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <CoproForm onClose={() => setShowForm(false)}
          onSaved={(c) => { setShowForm(false); navigate(`/coproprietes/${c.id}`) }} />
      )}
      {editCopro && (
        <CoproForm copro={editCopro} onClose={() => setEditCopro(null)}
          onSaved={() => { setEditCopro(null); fetch() }} />
      )}
      <ConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Supprimer la copropriété"
        message="Cette action est irréversible et supprime aussi ses lots et clés de répartition. Continuer ?"
        isLoading={deleting}
      />
    </div>
  )
}
