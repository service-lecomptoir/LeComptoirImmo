import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil, Plus, Trash2, Check, X, Building, MapPin } from 'lucide-react'
import { Button, Input } from '@/components/ui'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'
import { canManage } from '@/utils/permissions'
import { getErrorMessage } from '@/utils/errors'
import { coproApi, type CoproDetail as Detail, type CoproLot } from '@/api/coproprietes'
import { CoproForm } from './CoproForm'
import { CoproLotForm } from './CoproLotForm'
import { CoproBudgetTab } from './CoproBudgetTab'
import { CoproAccountsTab } from './CoproAccountsTab'
import { CoproRegulTab } from './CoproRegulTab'
import { CoproAssembliesTab } from './CoproAssembliesTab'
import { CoproWorksFundTab, CoproMaintenanceTab } from './CoproExtrasTabs'

type Tab = 'lots' | 'budget' | 'comptes' | 'regul' | 'ag' | 'fonds' | 'entretien'

export default function CoproDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [copro, setCopro] = useState<Detail | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('lots')
  const [editCopro, setEditCopro] = useState(false)
  const [lotForm, setLotForm] = useState<{ lot?: CoproLot } | null>(null)
  const [deleteLotId, setDeleteLotId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const user = useAuthStore(s => s.user)
  const canWrite = canManage(user?.role)

  // Ajout d'une clé
  const [keyName, setKeyName] = useState('')
  const [keyTotal, setKeyTotal] = useState('10000')
  const [editKeyId, setEditKeyId] = useState<string | null>(null)
  const [editKeyName, setEditKeyName] = useState('')
  const [editKeyTotal, setEditKeyTotal] = useState('')
  const [deleteKeyId, setDeleteKeyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await coproApi.get(id)
      setCopro(data)
    } catch (e) {
      toast.error(getErrorMessage(e, 'Copropriété introuvable'))
      navigate('/coproprietes')
    } finally { setLoading(false) }
  }, [id, navigate])

  useEffect(() => { load() }, [load])

  const addKey = async () => {
    if (!keyName.trim()) { toast.error('Nom de la clé requis.'); return }
    try {
      await coproApi.addKey(id, { name: keyName.trim(), total_tantiemes: Number(keyTotal) || 10000 })
      setKeyName(''); setKeyTotal('10000')
      toast.success('Clé ajoutée')
      load()
    } catch (e) { toast.error(getErrorMessage(e, "Erreur lors de l'ajout de la clé")) }
  }

  const saveKey = async (keyId: string) => {
    try {
      await coproApi.updateKey(id, keyId, { name: editKeyName.trim(), total_tantiemes: Number(editKeyTotal) || 0 })
      setEditKeyId(null)
      toast.success('Clé mise à jour')
      load()
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la mise à jour de la clé')) }
  }

  const removeKey = async () => {
    if (!deleteKeyId) return
    try {
      await coproApi.deleteKey(id, deleteKeyId)
      setDeleteKeyId(null)
      toast.success('Clé supprimée')
      load()
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  const removeLot = async () => {
    if (!deleteLotId) return
    setDeleting(true)
    try {
      await coproApi.deleteLot(id, deleteLotId)
      setDeleteLotId(null)
      toast.success('Lot supprimé')
      load()
    } finally { setDeleting(false) }
  }

  if (loading || !copro) return <div className="p-6 text-sm text-gray-400">Chargement…</div>

  return (
    <div className="p-4 sm:p-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/coproprietes')} className="p-1.5 rounded hover:bg-gray-100 text-gray-500" title="Retour">
            <ArrowLeft size={18} />
          </button>
          <span className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <Building size={18} className="text-blue-600" />
          </span>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{copro.name}</h1>
            <p className="text-sm text-gray-500">
              {copro.ref_code}{copro.immatriculation ? ` · ${copro.immatriculation}` : ''}
            </p>
          </div>
        </div>
        {canWrite && (
          <Button variant="secondary" onClick={() => setEditCopro(true)} leftIcon={<Pencil size={15} />}>Modifier</Button>
        )}
      </div>

      {/* Infos */}
      {(copro.address || copro.construction_year) && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-sm text-gray-700 flex flex-wrap gap-x-8 gap-y-2">
          {copro.address && (
            <span className="flex items-center gap-1.5"><MapPin size={14} className="text-gray-400" />
              {[copro.address, copro.zip_code, copro.city].filter(Boolean).join(', ')}
            </span>
          )}
          {copro.construction_year && <span>Construction : <strong>{copro.construction_year}</strong></span>}
        </div>
      )}

      {/* Onglets */}
      <div className="flex gap-1 border-b border-gray-200">
        {([['lots', 'Lots & clés'], ['budget', 'Budget & appels'], ['comptes', 'Comptes'], ['regul', 'Régularisation'], ['ag', 'Assemblées'], ['fonds', 'Fonds travaux'], ['entretien', 'Entretien']] as [Tab, string][]).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'budget' && <CoproBudgetTab copro={copro} canWrite={canWrite} />}
      {tab === 'comptes' && <CoproAccountsTab coproId={copro.id} />}
      {tab === 'regul' && <CoproRegulTab copro={copro} canWrite={canWrite} />}
      {tab === 'ag' && <CoproAssembliesTab copro={copro} canWrite={canWrite} />}
      {tab === 'fonds' && <CoproWorksFundTab coproId={copro.id} canWrite={canWrite} />}
      {tab === 'entretien' && <CoproMaintenanceTab coproId={copro.id} canWrite={canWrite} />}

      {tab === 'lots' && (<>
      {/* Clés de répartition */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-900">Clés de répartition</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase">
              <th className="px-4 py-2">Clé</th>
              <th className="px-4 py-2 text-right">Base</th>
              <th className="px-4 py-2 text-right">Affecté</th>
              <th className="px-4 py-2">État</th>
              {canWrite && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {copro.keys.map(k => (
              <tr key={k.id} className="border-t border-gray-100">
                {editKeyId === k.id ? (
                  <>
                    <td className="px-4 py-2"><Input value={editKeyName} onChange={e => setEditKeyName(e.target.value)} /></td>
                    <td className="px-4 py-2"><Input type="number" value={editKeyTotal} onChange={e => setEditKeyTotal(e.target.value)} className="text-right" /></td>
                    <td className="px-4 py-2 text-right text-gray-400">{k.assigned_tantiemes}</td>
                    <td className="px-4 py-2" colSpan={canWrite ? 2 : 1}>
                      <div className="flex gap-1">
                        <button onClick={() => saveKey(k.id)} className="p-1.5 rounded hover:bg-green-50 text-green-600" title="Enregistrer"><Check size={15} /></button>
                        <button onClick={() => setEditKeyId(null)} className="p-1.5 rounded hover:bg-gray-100 text-gray-500" title="Annuler"><X size={15} /></button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-2 font-medium text-gray-900">{k.name}{k.is_general && <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-full">générale</span>}</td>
                    <td className="px-4 py-2 text-right">{k.total_tantiemes}</td>
                    <td className="px-4 py-2 text-right">{k.assigned_tantiemes}</td>
                    <td className="px-4 py-2">
                      {k.balanced
                        ? <span className="text-xs text-green-700 bg-green-50 rounded-full px-2 py-0.5">Équilibrée</span>
                        : <span className="text-xs text-amber-700 bg-amber-50 rounded-full px-2 py-0.5">Écart {(k.assigned_tantiemes - k.total_tantiemes).toFixed(2)}</span>}
                    </td>
                    {canWrite && (
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-1">
                          <button onClick={() => { setEditKeyId(k.id); setEditKeyName(k.name); setEditKeyTotal(String(k.total_tantiemes)) }}
                            className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600" title="Modifier"><Pencil size={14} /></button>
                          <button onClick={() => setDeleteKeyId(k.id)}
                            className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button>
                        </div>
                      </td>
                    )}
                  </>
                )}
              </tr>
            ))}
            {copro.keys.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-3 text-gray-400">Aucune clé de répartition.</td></tr>
            )}
          </tbody>
        </table>
        {canWrite && (
          <div className="flex flex-wrap items-end gap-2 px-4 py-3 bg-gray-50 border-t border-gray-100">
            <div>
              <label className="block text-[11px] text-gray-600 mb-1">Nouvelle clé</label>
              <Input value={keyName} onChange={e => setKeyName(e.target.value)} placeholder="Ascenseur" />
            </div>
            <div>
              <label className="block text-[11px] text-gray-600 mb-1">Base</label>
              <Input type="number" value={keyTotal} onChange={e => setKeyTotal(e.target.value)} className="w-28" />
            </div>
            <Button variant="secondary" onClick={addKey} leftIcon={<Plus size={15} />}>Ajouter</Button>
          </div>
        )}
      </div>

      {/* Lots */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between bg-gray-50 px-4 py-2.5 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-900">Lots ({copro.lots.length})</h2>
          {canWrite && (
            <Button size="sm" onClick={() => setLotForm({})} leftIcon={<Plus size={15} />}>Ajouter un lot</Button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase">
                <th className="px-4 py-2">Lot</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Copropriétaire</th>
                {copro.keys.map(k => <th key={k.id} className="px-4 py-2 text-right">{k.name}</th>)}
                {canWrite && <th className="px-4 py-2" />}
              </tr>
            </thead>
            <tbody>
              {copro.lots.map(lot => (
                <tr key={lot.id} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-medium text-gray-900">{lot.numero}{lot.floor ? <span className="text-gray-400 font-normal"> · {lot.floor}</span> : ''}</td>
                  <td className="px-4 py-2 text-gray-600">{lot.lot_type || '-'}</td>
                  <td className="px-4 py-2 text-gray-600">{lot.owner_name || <span className="text-gray-300">—</span>}</td>
                  {copro.keys.map(k => <td key={k.id} className="px-4 py-2 text-right">{lot.tantiemes[k.id] ?? 0}</td>)}
                  {canWrite && (
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setLotForm({ lot })} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600" title="Modifier"><Pencil size={14} /></button>
                        <button onClick={() => setDeleteLotId(lot.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {copro.lots.length === 0 && (
                <tr><td colSpan={4 + copro.keys.length} className="px-4 py-3 text-gray-400">Aucun lot.</td></tr>
              )}
            </tbody>
            {copro.lots.length > 0 && (
              <tfoot>
                <tr className="border-t border-gray-200 bg-gray-50 font-medium">
                  <td className="px-4 py-2" colSpan={3}>Total affecté</td>
                  {copro.keys.map(k => (
                    <td key={k.id} className={`px-4 py-2 text-right ${k.balanced ? 'text-green-700' : 'text-amber-700'}`}>
                      {k.assigned_tantiemes} / {k.total_tantiemes}
                    </td>
                  ))}
                  {canWrite && <td />}
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
      </>)}

      {/* Modals */}
      {editCopro && (
        <CoproForm copro={copro} onClose={() => setEditCopro(false)}
          onSaved={(c) => { setEditCopro(false); setCopro(c) }} />
      )}
      {lotForm && (
        <CoproLotForm copro={copro} lot={lotForm.lot} onClose={() => setLotForm(null)}
          onSaved={() => { setLotForm(null); load() }} />
      )}
      <ConfirmDialog isOpen={!!deleteLotId} onClose={() => setDeleteLotId(null)} onConfirm={removeLot}
        title="Supprimer le lot" message="Cette action est irréversible. Continuer ?" isLoading={deleting} />
      <ConfirmDialog isOpen={!!deleteKeyId} onClose={() => setDeleteKeyId(null)} onConfirm={removeKey}
        title="Supprimer la clé de répartition"
        message="Les tantièmes des lots pour cette clé seront aussi supprimés. Continuer ?" />
    </div>
  )
}
