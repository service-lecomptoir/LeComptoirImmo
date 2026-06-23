import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, FileDown } from 'lucide-react'
import { Button, Input } from '@/components/ui'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import { formatEuro as fmtEuro } from '@/utils/format'
import { docFilename } from '@/utils/filename'
import {
  coproApi, type CoproDetail, type CoproExpense, type RegularizationResult,
} from '@/api/coproprietes'

export function CoproRegulTab({ copro, canWrite }: { copro: CoproDetail; canWrite: boolean }) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [expenses, setExpenses] = useState<CoproExpense[]>([])
  const [regul, setRegul] = useState<RegularizationResult | null>(null)
  const [loading, setLoading] = useState(true)
  // Formulaire d'ajout de dépense
  const [label, setLabel] = useState('')
  const [keyId, setKeyId] = useState(copro.keys[0]?.id ?? '')
  const [amount, setAmount] = useState('')
  const [expDate, setExpDate] = useState('')
  const [supplier, setSupplier] = useState('')
  const [saving, setSaving] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  const years = [now.getFullYear() + 1, now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2]

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [e, r] = await Promise.all([
        coproApi.listExpenses(copro.id, year),
        coproApi.regularization(copro.id, year),
      ])
      setExpenses(e.data)
      setRegul(r.data)
    } catch (err) {
      toast.error(getErrorMessage(err, 'Erreur lors du chargement de la régularisation'))
    } finally { setLoading(false) }
  }, [copro.id, year])

  useEffect(() => { load() }, [load])

  const addExpense = async () => {
    if (!label.trim()) { toast.error('Libellé requis.'); return }
    if (!keyId) { toast.error('Choisissez une clé.'); return }
    const n = parseFloat(amount.replace(',', '.'))
    if (!n || n <= 0) { toast.error('Montant invalide.'); return }
    setSaving(true)
    try {
      await coproApi.createExpense(copro.id, {
        year, key_id: keyId, label: label.trim(), amount: n,
        expense_date: expDate || null, supplier: supplier.trim() || null,
      })
      toast.success('Dépense ajoutée')
      setLabel(''); setAmount(''); setExpDate(''); setSupplier('')
      load()
    } catch (e) {
      toast.error(getErrorMessage(e, "Erreur lors de l'ajout de la dépense"))
    } finally { setSaving(false) }
  }

  const removeExpense = async (id: string) => {
    if (!window.confirm('Supprimer cette dépense ?')) return
    try {
      await coproApi.deleteExpense(copro.id, id)
      toast.success('Dépense supprimée')
      load()
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  const downloadRegul = async (ownerId: string, ownerName: string) => {
    setDownloadingId(ownerId)
    try {
      await coproApi.regulPdf(copro.id, ownerId, year, docFilename('regularisation', { tenant: ownerName, year }))
    } catch (e) {
      toast.error(getErrorMessage(e, 'Erreur lors du téléchargement du décompte'))
    } finally { setDownloadingId(null) }
  }

  if (loading) return <p className="text-sm text-gray-400 py-4">Chargement…</p>

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <label className="text-sm text-gray-600">Année</label>
        <select value={year} onChange={e => setYear(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
          {years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      {/* Dépenses réelles */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">Dépenses réelles {year}</h3>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 uppercase">
            <th className="px-4 py-2">Date</th><th className="px-4 py-2">Poste</th><th className="px-4 py-2">Clé</th>
            <th className="px-4 py-2">Fournisseur</th><th className="px-4 py-2 text-right">Montant</th>{canWrite && <th className="px-4 py-2" />}
          </tr></thead>
          <tbody>
            {expenses.map(e => (
              <tr key={e.id} className="border-t border-gray-100">
                <td className="px-4 py-2 whitespace-nowrap">{e.expense_date ? new Date(e.expense_date).toLocaleDateString('fr-FR') : '-'}</td>
                <td className="px-4 py-2">{e.label}</td>
                <td className="px-4 py-2 text-gray-600">{e.key_name}</td>
                <td className="px-4 py-2 text-gray-500">{e.supplier || '-'}</td>
                <td className="px-4 py-2 text-right">{fmtEuro(e.amount)}</td>
                {canWrite && (
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => removeExpense(e.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button>
                  </td>
                )}
              </tr>
            ))}
            {expenses.length === 0 && <tr><td colSpan={6} className="px-4 py-3 text-gray-400">Aucune dépense saisie.</td></tr>}
          </tbody>
          <tfoot>
            <tr className="border-t border-gray-200 bg-gray-50 font-medium">
              <td className="px-4 py-2" colSpan={4}>Total dépenses</td>
              <td className="px-4 py-2 text-right">{fmtEuro(regul?.expenses_total ?? 0)}</td>{canWrite && <td />}
            </tr>
          </tfoot>
        </table>
        {canWrite && (
          <div className="flex flex-wrap items-end gap-2 px-4 py-3 bg-gray-50 border-t border-gray-100">
            <div><label className="block text-[11px] text-gray-600 mb-1">Libellé</label>
              <Input value={label} onChange={e => setLabel(e.target.value)} placeholder="Entretien ascenseur" /></div>
            <div><label className="block text-[11px] text-gray-600 mb-1">Clé</label>
              <select value={keyId} onChange={e => setKeyId(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
                {copro.keys.map(k => <option key={k.id} value={k.id}>{k.name}</option>)}
              </select></div>
            <div><label className="block text-[11px] text-gray-600 mb-1">Montant (€)</label>
              <Input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} className="w-28" /></div>
            <div><label className="block text-[11px] text-gray-600 mb-1">Date</label>
              <input type="date" value={expDate} onChange={e => setExpDate(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm" /></div>
            <div><label className="block text-[11px] text-gray-600 mb-1">Fournisseur</label>
              <Input value={supplier} onChange={e => setSupplier(e.target.value)} placeholder="(optionnel)" /></div>
            <Button size="sm" onClick={addExpense} isLoading={saving} leftIcon={<Plus size={14} />}>Ajouter</Button>
          </div>
        )}
      </div>

      {/* Régularisation par copropriétaire */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200 flex flex-wrap gap-x-6 gap-y-1">
          <h3 className="text-sm font-semibold text-gray-900">Régularisation {year}</h3>
          <span className="text-xs text-gray-500">Budget : <strong>{fmtEuro(regul?.budget_total ?? 0)}</strong></span>
          <span className="text-xs text-gray-500">Appelé : <strong>{fmtEuro(regul?.appele_total ?? 0)}</strong></span>
          <span className="text-xs text-gray-500">Dépenses : <strong>{fmtEuro(regul?.expenses_total ?? 0)}</strong></span>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 uppercase">
            <th className="px-4 py-2">Copropriétaire</th>
            <th className="px-4 py-2 text-right">Appelé</th>
            <th className="px-4 py-2 text-right">Charges réelles</th>
            <th className="px-4 py-2 text-right">Solde</th>
            <th className="px-4 py-2" />
          </tr></thead>
          <tbody>
            {(regul?.rows ?? []).map((r, i) => (
              <tr key={r.owner_id ?? i} className="border-t border-gray-100">
                <td className="px-4 py-2 font-medium text-gray-900">{r.owner_name}</td>
                <td className="px-4 py-2 text-right">{fmtEuro(r.appele)}</td>
                <td className="px-4 py-2 text-right">{fmtEuro(r.reel)}</td>
                <td className={`px-4 py-2 text-right font-medium ${r.solde >= 0 ? 'text-green-700' : 'text-amber-700'}`}>
                  {fmtEuro(r.solde)} <span className="text-[10px] font-normal text-gray-400">{r.solde >= 0 ? 'à reverser' : 'à appeler'}</span>
                </td>
                <td className="px-4 py-2 text-right">
                  {r.owner_id && (
                    <button onClick={() => downloadRegul(r.owner_id!, r.owner_name || 'coproprietaire')}
                      disabled={downloadingId === r.owner_id}
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50">
                      <FileDown size={13} /> Décompte
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {(!regul || regul.rows.length === 0) && <tr><td colSpan={5} className="px-4 py-3 text-gray-400">Rien à régulariser (ni appels ni dépenses sur {year}).</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
