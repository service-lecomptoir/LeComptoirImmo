import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, FileDown, Save } from 'lucide-react'
import { Button, Input } from '@/components/ui'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import { formatEuro as fmtEuro } from '@/utils/format'
import { docFilename } from '@/utils/filename'
import {
  coproApi, type CoproDetail, type Budget, type FundCall, type Periodicity,
} from '@/api/coproprietes'

const PERIODICITIES: { value: Periodicity; label: string }[] = [
  { value: 'mensuel', label: 'Mensuel (12)' },
  { value: 'trimestriel', label: 'Trimestriel (4)' },
  { value: 'semestriel', label: 'Semestriel (2)' },
  { value: 'annuel', label: 'Annuel (1)' },
]
const STATUS: Record<string, { label: string; cls: string }> = {
  pending: { label: 'En attente', cls: 'text-gray-500 bg-gray-100' },
  partial: { label: 'Partiel', cls: 'text-amber-700 bg-amber-50' },
  paid: { label: 'Payé', cls: 'text-green-700 bg-green-50' },
}

type LineDraft = { key_id: string; label: string; amount: string }

export function CoproBudgetTab({ copro, canWrite }: { copro: CoproDetail; canWrite: boolean }) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [budget, setBudget] = useState<Budget | null>(null)
  const [loading, setLoading] = useState(true)
  const [periodicity, setPeriodicity] = useState<Periodicity>('trimestriel')
  const [lines, setLines] = useState<LineDraft[]>([])
  const [saving, setSaving] = useState(false)
  const [calls, setCalls] = useState<FundCall[]>([])
  const [genIndex, setGenIndex] = useState(1)
  const [genDue, setGenDue] = useState('')
  const [generating, setGenerating] = useState(false)
  const [deleteCallId, setDeleteCallId] = useState<string | null>(null)
  const [payItem, setPayItem] = useState<string | null>(null)
  const [payAmount, setPayAmount] = useState('')
  const [payDate, setPayDate] = useState(now.toISOString().slice(0, 10))

  const years = [now.getFullYear() + 1, now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2]
  const NB: Record<Periodicity, number> = { mensuel: 12, trimestriel: 4, semestriel: 2, annuel: 1 }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await coproApi.getBudget(copro.id, year)
      setBudget(data)
      if (data) {
        setPeriodicity(data.periodicity)
        setLines(data.lines.map(l => ({ key_id: l.key_id, label: l.label, amount: String(l.amount) })))
        const c = await coproApi.listCalls(copro.id, data.id)
        setCalls(c.data)
      } else {
        // Pré-remplir une ligne par clé.
        setPeriodicity('trimestriel')
        setLines(copro.keys.map(k => ({ key_id: k.id, label: k.name, amount: '' })))
        setCalls([])
      }
    } catch (e) {
      toast.error(getErrorMessage(e, 'Erreur lors du chargement du budget'))
    } finally { setLoading(false) }
  }, [copro.id, copro.keys, year])

  useEffect(() => { load() }, [load])

  const setLine = (i: number, patch: Partial<LineDraft>) =>
    setLines(prev => prev.map((l, idx) => idx === i ? { ...l, ...patch } : l))
  const addLine = () => setLines(prev => [...prev, { key_id: copro.keys[0]?.id ?? '', label: '', amount: '' }])
  const removeLine = (i: number) => setLines(prev => prev.filter((_, idx) => idx !== i))

  const total = lines.reduce((s, l) => s + (parseFloat((l.amount || '0').replace(',', '.')) || 0), 0)

  const saveBudget = async () => {
    const payloadLines = lines
      .filter(l => l.key_id && l.label.trim())
      .map(l => ({ key_id: l.key_id, label: l.label.trim(), amount: parseFloat((l.amount || '0').replace(',', '.')) || 0 }))
    setSaving(true)
    try {
      if (budget) {
        await coproApi.updateBudget(copro.id, budget.id, { periodicity, lines: payloadLines })
        toast.success('Budget mis à jour')
      } else {
        await coproApi.createBudget(copro.id, { year, periodicity, lines: payloadLines })
        toast.success('Budget créé')
      }
      load()
    } catch (e) {
      toast.error(getErrorMessage(e, "Erreur lors de l'enregistrement du budget"))
    } finally { setSaving(false) }
  }

  const generate = async () => {
    if (!budget) return
    setGenerating(true)
    try {
      await coproApi.generateCall(copro.id, budget.id, genIndex, genDue || null)
      toast.success('Appel de fonds généré')
      setGenDue('')
      load()
    } catch (e) {
      toast.error(getErrorMessage(e, "Erreur lors de la génération de l'appel"))
    } finally { setGenerating(false) }
  }

  const removeCall = async () => {
    if (!deleteCallId) return
    try {
      await coproApi.deleteCall(copro.id, deleteCallId)
      setDeleteCallId(null)
      toast.success('Appel supprimé')
      load()
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  const submitPayment = async (itemId: string) => {
    const n = parseFloat(payAmount.replace(',', '.'))
    if (!n || n <= 0) { toast.error('Montant invalide.'); return }
    try {
      await coproApi.recordPayment(copro.id, itemId, { amount: n, payment_date: payDate })
      toast.success('Encaissement enregistré')
      setPayItem(null); setPayAmount('')
      load()
    } catch (e) { toast.error(getErrorMessage(e, "Erreur lors de l'encaissement")) }
  }

  const downloadAppel = async (itemId: string, ownerName: string, periodLabel: string) => {
    try {
      await coproApi.appelPdf(copro.id, itemId, docFilename('appel-fonds', { tenant: `${ownerName}_${periodLabel}` }))
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors du téléchargement')) }
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

      {/* Budget */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between bg-gray-50 px-4 py-2.5 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">Budget prévisionnel {year}</h3>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-600">Périodicité des appels</label>
            <select value={periodicity} onChange={e => setPeriodicity(e.target.value as Periodicity)}
              disabled={!canWrite}
              className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
              {PERIODICITIES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 uppercase">
            <th className="px-4 py-2">Poste</th><th className="px-4 py-2">Clé</th>
            <th className="px-4 py-2 text-right">Montant annuel</th>{canWrite && <th className="px-4 py-2" />}
          </tr></thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="px-4 py-2">
                  {canWrite
                    ? <Input value={l.label} onChange={e => setLine(i, { label: e.target.value })} placeholder="Libellé du poste" />
                    : l.label}
                </td>
                <td className="px-4 py-2">
                  {canWrite ? (
                    <select value={l.key_id} onChange={e => setLine(i, { key_id: e.target.value })}
                      className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
                      {copro.keys.map(k => <option key={k.id} value={k.id}>{k.name}</option>)}
                    </select>
                  ) : (copro.keys.find(k => k.id === l.key_id)?.name ?? '')}
                </td>
                <td className="px-4 py-2 text-right">
                  {canWrite
                    ? <Input type="number" step="0.01" value={l.amount} onChange={e => setLine(i, { amount: e.target.value })} className="text-right w-32" />
                    : fmtEuro(parseFloat(l.amount || '0'))}
                </td>
                {canWrite && (
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => removeLine(i)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Retirer"><Trash2 size={14} /></button>
                  </td>
                )}
              </tr>
            ))}
            {lines.length === 0 && <tr><td colSpan={4} className="px-4 py-3 text-gray-400">Aucun poste.</td></tr>}
          </tbody>
          <tfoot>
            <tr className="border-t border-gray-200 bg-gray-50 font-medium">
              <td className="px-4 py-2" colSpan={2}>Total budget</td>
              <td className="px-4 py-2 text-right">{fmtEuro(total)}</td>{canWrite && <td />}
            </tr>
          </tfoot>
        </table>
        {canWrite && (
          <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-t border-gray-100">
            <Button variant="secondary" size="sm" onClick={addLine} leftIcon={<Plus size={14} />}>Ajouter un poste</Button>
            <Button size="sm" onClick={saveBudget} isLoading={saving} leftIcon={<Save size={14} />}>
              {budget ? 'Enregistrer le budget' : 'Créer le budget'}
            </Button>
          </div>
        )}
      </div>

      {/* Appels de fonds */}
      {budget && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="flex flex-wrap items-end justify-between gap-2 bg-gray-50 px-4 py-2.5 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900">Appels de fonds</h3>
            {canWrite && (
              <div className="flex items-end gap-2">
                <div>
                  <label className="block text-[11px] text-gray-600 mb-1">Période</label>
                  <select value={genIndex} onChange={e => setGenIndex(Number(e.target.value))}
                    className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
                    {Array.from({ length: NB[periodicity] }, (_, i) => i + 1).map(p =>
                      <option key={p} value={p}>{periodicity === 'trimestriel' ? `T${p}` : periodicity === 'semestriel' ? `S${p}` : p}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-gray-600 mb-1">Échéance (option.)</label>
                  <input type="date" value={genDue} onChange={e => setGenDue(e.target.value)}
                    className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
                </div>
                <Button size="sm" onClick={generate} isLoading={generating} leftIcon={<Plus size={14} />}>Générer</Button>
              </div>
            )}
          </div>
          <div className="divide-y divide-gray-100">
            {calls.length === 0 && <p className="px-4 py-3 text-sm text-gray-400">Aucun appel de fonds généré.</p>}
            {calls.map(call => (
              <div key={call.id} className="px-4 py-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-gray-900">{call.period_label}
                    <span className="ml-2 text-xs text-gray-500">{fmtEuro(call.total_paid)} / {fmtEuro(call.total_due)} encaissé</span>
                  </p>
                  {canWrite && (
                    <button onClick={() => setDeleteCallId(call.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer l'appel"><Trash2 size={14} /></button>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[560px]">
                    <thead><tr className="text-left text-xs text-gray-500 uppercase">
                      <th className="px-3 py-1.5">Lot</th><th className="px-3 py-1.5">Copropriétaire</th>
                      <th className="px-3 py-1.5 text-right">Dû</th><th className="px-3 py-1.5 text-right">Payé</th>
                      <th className="px-3 py-1.5">Statut</th><th className="px-3 py-1.5" />
                    </tr></thead>
                    <tbody>
                      {call.items.map(it => (
                        <tr key={it.id} className="border-t border-gray-100">
                          <td className="px-3 py-1.5">{it.lot_numero || '-'}</td>
                          <td className="px-3 py-1.5">{it.owner_name || <span className="text-gray-300">—</span>}</td>
                          <td className="px-3 py-1.5 text-right">{fmtEuro(it.amount_due)}</td>
                          <td className="px-3 py-1.5 text-right text-green-700">{fmtEuro(it.amount_paid)}</td>
                          <td className="px-3 py-1.5"><span className={`text-xs rounded-full px-2 py-0.5 ${STATUS[it.status]?.cls}`}>{STATUS[it.status]?.label ?? it.status}</span></td>
                          <td className="px-3 py-1.5 text-right whitespace-nowrap">
                            {payItem === it.id ? (
                              <span className="inline-flex items-center gap-1">
                                <input type="number" step="0.01" value={payAmount} onChange={e => setPayAmount(e.target.value)}
                                  placeholder="Montant" className="w-24 px-2 py-1 border border-gray-300 rounded text-sm" />
                                <input type="date" value={payDate} onChange={e => setPayDate(e.target.value)}
                                  className="px-2 py-1 border border-gray-300 rounded text-sm" />
                                <button onClick={() => submitPayment(it.id)} className="px-2 py-1 bg-blue-600 text-white rounded text-xs">OK</button>
                                <button onClick={() => setPayItem(null)} className="px-2 py-1 text-gray-500 text-xs">✕</button>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1">
                                {canWrite && it.status !== 'paid' && (
                                  <button onClick={() => { setPayItem(it.id); setPayAmount(String((it.amount_due - it.amount_paid).toFixed(2))) }}
                                    className="text-xs text-blue-600 hover:text-blue-700">Encaisser</button>
                                )}
                                <button onClick={() => downloadAppel(it.id, it.owner_name || 'coproprietaire', call.period_label)}
                                  className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600" title="Appel de fonds PDF"><FileDown size={14} /></button>
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <ConfirmDialog isOpen={!!deleteCallId} onClose={() => setDeleteCallId(null)} onConfirm={removeCall}
        title="Supprimer l'appel de fonds" message="Les quote-parts et encaissements liés seront supprimés. Continuer ?" />
    </div>
  )
}
