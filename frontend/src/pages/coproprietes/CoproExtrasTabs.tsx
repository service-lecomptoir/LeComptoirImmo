import { useState, useEffect, useCallback, useRef } from 'react'
import { Plus, Trash2, PiggyBank, Wrench, Upload, FileText, Download } from 'lucide-react'
import { Button, Input } from '@/components/ui'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import { formatEuro as fmtEuro } from '@/utils/format'
import { coproApi, type WorksFundSummary, type Maintenance, type CoproDocument } from '@/api/coproprietes'

const today = () => new Date().toISOString().slice(0, 10)

function fmtSize(n?: number | null): string {
  if (!n) return ''
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} Ko`
  return `${(n / 1024 / 1024).toFixed(1)} Mo`
}

// ── Coffre de documents ───────────────────────────────────────────────────────
export function CoproDocumentsTab({ coproId, canWrite }: { coproId: string; canWrite: boolean }) {
  const [docs, setDocs] = useState<CoproDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setDocs((await coproApi.listDocuments(coproId)).data) }
    catch (e) { toast.error(getErrorMessage(e, 'Erreur lors du chargement des documents')) }
    finally { setLoading(false) }
  }, [coproId])
  useEffect(() => { load() }, [load])

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    if (f.size > 20 * 1024 * 1024) { toast.error('Fichier trop lourd (max 20 Mo).'); return }
    setBusy(true)
    try {
      await coproApi.uploadDocument(coproId, f)
      toast.success('Document ajouté'); load()
    } catch (err) { toast.error(getErrorMessage(err, "Échec du téléversement")) }
    finally { setBusy(false) }
  }

  const remove = async (id: string) => {
    if (!window.confirm('Supprimer ce document ?')) return
    try { await coproApi.deleteDocument(id); load() }
    catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  if (loading) return <p className="text-sm text-gray-400 py-4">Chargement…</p>

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between bg-gray-50 px-4 py-2.5 border-b border-gray-200">
        <div className="flex items-center gap-2"><FileText size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-900">Coffre de documents</h3></div>
        {canWrite && (
          <>
            <Button size="sm" onClick={() => fileRef.current?.click()} isLoading={busy} leftIcon={<Upload size={14} />}>Téléverser</Button>
            <input ref={fileRef} type="file" className="hidden" onChange={onPick}
              accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx" />
          </>
        )}
      </div>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-gray-500 uppercase">
          <th className="px-4 py-2">Document</th><th className="px-4 py-2">Ajouté le</th>
          <th className="px-4 py-2 text-right">Taille</th><th className="px-4 py-2" />
        </tr></thead>
        <tbody>
          {docs.map(d => (
            <tr key={d.id} className="border-t border-gray-100">
              <td className="px-4 py-2">{d.label || d.file_name}</td>
              <td className="px-4 py-2 text-gray-500">{new Date(d.created_at).toLocaleDateString('fr-FR')}</td>
              <td className="px-4 py-2 text-right text-gray-400">{fmtSize(d.file_size)}</td>
              <td className="px-4 py-2 text-right">
                <div className="inline-flex gap-1">
                  <button onClick={() => coproApi.downloadDocument(d.id, d.file_name)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600" title="Télécharger"><Download size={14} /></button>
                  {canWrite && <button onClick={() => remove(d.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button>}
                </div>
              </td>
            </tr>
          ))}
          {docs.length === 0 && <tr><td colSpan={4} className="px-4 py-3 text-gray-400">Aucun document.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

// ── Fonds de travaux (ALUR) ───────────────────────────────────────────────────
export function CoproWorksFundTab({ coproId, canWrite }: { coproId: string; canWrite: boolean }) {
  const [fund, setFund] = useState<WorksFundSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [kind, setKind] = useState<'contribution' | 'depense'>('contribution')
  const [label, setLabel] = useState('')
  const [amount, setAmount] = useState('')
  const [edate, setEdate] = useState(today())
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try { setFund((await coproApi.worksFund(coproId)).data) }
    catch (e) { toast.error(getErrorMessage(e, 'Erreur lors du chargement du fonds de travaux')) }
    finally { setLoading(false) }
  }, [coproId])
  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!label.trim()) { toast.error('Libellé requis.'); return }
    const n = parseFloat(amount.replace(',', '.'))
    if (!n || n <= 0) { toast.error('Montant invalide.'); return }
    setSaving(true)
    try {
      await coproApi.addWorksEntry(coproId, { entry_date: edate, kind, label: label.trim(), amount: n })
      toast.success('Mouvement enregistré'); setLabel(''); setAmount(''); load()
    } catch (e) { toast.error(getErrorMessage(e, "Erreur lors de l'enregistrement")) }
    finally { setSaving(false) }
  }
  const remove = async (id: string) => {
    if (!window.confirm('Supprimer ce mouvement ?')) return
    try { await coproApi.deleteWorksEntry(coproId, id); load() }
    catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  if (loading || !fund) return <p className="text-sm text-gray-400 py-4">Chargement…</p>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div className="bg-white rounded-lg border border-gray-200 p-3 text-center"><p className="text-base font-bold text-green-700">{fmtEuro(fund.total_contributions)}</p><p className="text-[11px] text-gray-500">Cotisations</p></div>
        <div className="bg-white rounded-lg border border-gray-200 p-3 text-center"><p className="text-base font-bold text-red-700">{fmtEuro(fund.total_depenses)}</p><p className="text-[11px] text-gray-500">Dépenses travaux</p></div>
        <div className="bg-white rounded-lg border border-gray-200 p-3 text-center"><p className="text-base font-bold text-blue-700">{fmtEuro(fund.balance)}</p><p className="text-[11px] text-gray-500">Solde du fonds</p></div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center gap-2 bg-gray-50 px-4 py-2.5 border-b border-gray-200">
          <PiggyBank size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-900">Fonds de travaux (loi ALUR)</h3>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 uppercase">
            <th className="px-4 py-2">Date</th><th className="px-4 py-2">Mouvement</th><th className="px-4 py-2">Libellé</th>
            <th className="px-4 py-2 text-right">Montant</th>{canWrite && <th className="px-4 py-2" />}
          </tr></thead>
          <tbody>
            {fund.entries.map(e => (
              <tr key={e.id} className="border-t border-gray-100">
                <td className="px-4 py-2 whitespace-nowrap">{new Date(e.entry_date).toLocaleDateString('fr-FR')}</td>
                <td className="px-4 py-2">{e.kind === 'contribution' ? <span className="text-green-700">Cotisation</span> : <span className="text-red-700">Dépense</span>}</td>
                <td className="px-4 py-2">{e.label}</td>
                <td className="px-4 py-2 text-right">{fmtEuro(e.amount)}</td>
                {canWrite && <td className="px-4 py-2 text-right"><button onClick={() => remove(e.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button></td>}
              </tr>
            ))}
            {fund.entries.length === 0 && <tr><td colSpan={5} className="px-4 py-3 text-gray-400">Aucun mouvement.</td></tr>}
          </tbody>
        </table>
        {canWrite && (
          <div className="flex flex-wrap items-end gap-2 px-4 py-3 bg-gray-50 border-t border-gray-100">
            <div><label className="block text-[11px] text-gray-600 mb-1">Type</label>
              <select value={kind} onChange={e => setKind(e.target.value as 'contribution' | 'depense')} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
                <option value="contribution">Cotisation</option><option value="depense">Dépense travaux</option>
              </select></div>
            <div className="flex-1 min-w-[160px]"><label className="block text-[11px] text-gray-600 mb-1">Libellé</label>
              <Input value={label} onChange={e => setLabel(e.target.value)} placeholder="Cotisation annuelle / Ravalement" /></div>
            <div><label className="block text-[11px] text-gray-600 mb-1">Montant (€)</label>
              <Input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} className="w-28" /></div>
            <div><label className="block text-[11px] text-gray-600 mb-1">Date</label>
              <input type="date" value={edate} onChange={e => setEdate(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm" /></div>
            <Button size="sm" onClick={add} isLoading={saving} leftIcon={<Plus size={14} />}>Ajouter</Button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Carnet d'entretien ────────────────────────────────────────────────────────
export function CoproMaintenanceTab({ coproId, canWrite }: { coproId: string; canWrite: boolean }) {
  const [rows, setRows] = useState<Maintenance[]>([])
  const [loading, setLoading] = useState(true)
  const [edate, setEdate] = useState(today())
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [supplier, setSupplier] = useState('')
  const [cost, setCost] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await coproApi.listMaintenance(coproId)).data) }
    catch (e) { toast.error(getErrorMessage(e, 'Erreur lors du chargement du carnet')) }
    finally { setLoading(false) }
  }, [coproId])
  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!description.trim()) { toast.error('Description requise.'); return }
    setSaving(true)
    try {
      await coproApi.addMaintenance(coproId, {
        entry_date: edate || null, category: category.trim() || null, description: description.trim(),
        supplier: supplier.trim() || null, cost: cost ? parseFloat(cost.replace(',', '.')) : null,
      })
      toast.success('Entrée ajoutée'); setCategory(''); setDescription(''); setSupplier(''); setCost(''); load()
    } catch (e) { toast.error(getErrorMessage(e, "Erreur lors de l'ajout")) }
    finally { setSaving(false) }
  }
  const remove = async (id: string) => {
    if (!window.confirm('Supprimer cette entrée ?')) return
    try { await coproApi.deleteMaintenance(coproId, id); load() }
    catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  if (loading) return <p className="text-sm text-gray-400 py-4">Chargement…</p>

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center gap-2 bg-gray-50 px-4 py-2.5 border-b border-gray-200">
        <Wrench size={16} className="text-blue-600" />
        <h3 className="text-sm font-semibold text-gray-900">Carnet d'entretien</h3>
      </div>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-gray-500 uppercase">
          <th className="px-4 py-2">Date</th><th className="px-4 py-2">Catégorie</th><th className="px-4 py-2">Description</th>
          <th className="px-4 py-2">Fournisseur</th><th className="px-4 py-2 text-right">Coût</th>{canWrite && <th className="px-4 py-2" />}
        </tr></thead>
        <tbody>
          {rows.map(m => (
            <tr key={m.id} className="border-t border-gray-100">
              <td className="px-4 py-2 whitespace-nowrap">{m.entry_date ? new Date(m.entry_date).toLocaleDateString('fr-FR') : '-'}</td>
              <td className="px-4 py-2 text-gray-600">{m.category || '-'}</td>
              <td className="px-4 py-2">{m.description}</td>
              <td className="px-4 py-2 text-gray-500">{m.supplier || '-'}</td>
              <td className="px-4 py-2 text-right">{m.cost != null ? fmtEuro(m.cost) : '-'}</td>
              {canWrite && <td className="px-4 py-2 text-right"><button onClick={() => remove(m.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button></td>}
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={6} className="px-4 py-3 text-gray-400">Aucune entrée d'entretien.</td></tr>}
        </tbody>
      </table>
      {canWrite && (
        <div className="flex flex-wrap items-end gap-2 px-4 py-3 bg-gray-50 border-t border-gray-100">
          <div><label className="block text-[11px] text-gray-600 mb-1">Date</label>
            <input type="date" value={edate} onChange={e => setEdate(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm" /></div>
          <div><label className="block text-[11px] text-gray-600 mb-1">Catégorie</label>
            <Input value={category} onChange={e => setCategory(e.target.value)} placeholder="Ascenseur" className="w-32" /></div>
          <div className="flex-1 min-w-[180px]"><label className="block text-[11px] text-gray-600 mb-1">Description</label>
            <Input value={description} onChange={e => setDescription(e.target.value)} placeholder="Visite de maintenance annuelle" /></div>
          <div><label className="block text-[11px] text-gray-600 mb-1">Fournisseur</label>
            <Input value={supplier} onChange={e => setSupplier(e.target.value)} placeholder="(optionnel)" className="w-32" /></div>
          <div><label className="block text-[11px] text-gray-600 mb-1">Coût (€)</label>
            <Input type="number" step="0.01" value={cost} onChange={e => setCost(e.target.value)} className="w-24" /></div>
          <Button size="sm" onClick={add} isLoading={saving} leftIcon={<Plus size={14} />}>Ajouter</Button>
        </div>
      )}
    </div>
  )
}
