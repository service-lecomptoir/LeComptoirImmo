import { useState, useEffect } from 'react'
import { ChevronRight, ChevronDown, FileDown, RefreshCw, KeyRound, Wallet, Plus, Trash2 } from 'lucide-react'
import { ownersApi, type MandantAccount } from '@/api/owners'
import type { OwnerListItem } from '@/types/owner'
import { docFilename } from '@/utils/filename'
import { formatEuro as fmtEuro } from '@/utils/format'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

const METHOD_LABELS: Record<string, string> = {
  virement: 'Virement', cheque: 'Chèque', especes: 'Espèces', autre: 'Autre',
}

/** Compta mandant : compte rendu de gestion par propriétaire (honoraires, net,
 *  reversements, solde à reverser) avec export CRG PDF. Rôle mandataire. */
export default function ComptaMandant() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [owners, setOwners] = useState<OwnerListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [data, setData] = useState<Record<string, MandantAccount>>({})
  const [fetchingId, setFetchingId] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    ownersApi.list({ limit: 200 })
      .then(r => setOwners(r.data.items))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { setData({}); setExpandedId(null) }, [year])

  const load = async (ownerId: string) => {
    const key = `${ownerId}:${year}`
    setFetchingId(ownerId)
    try {
      const r = await ownersApi.mandant(ownerId, year)
      setData(prev => ({ ...prev, [key]: r.data }))
    } catch (e) {
      toast.error(getErrorMessage(e, 'Erreur lors du chargement du compte mandant'))
    } finally { setFetchingId(null) }
  }

  const toggle = async (o: OwnerListItem) => {
    if (expandedId === o.id) { setExpandedId(null); return }
    setExpandedId(o.id)
    if (!data[`${o.id}:${year}`]) await load(o.id)
  }

  const downloadCrg = async (o: OwnerListItem) => {
    setDownloadingId(o.id)
    try {
      await ownersApi.crgPdf(o.id, year, docFilename('crg', { tenant: o.full_name, year }))
    } catch (e) {
      toast.error(getErrorMessage(e, 'Erreur lors du téléchargement du CRG'))
    } finally { setDownloadingId(null) }
  }

  const years = [now.getFullYear() + 1, now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2]

  return (
    <div className="p-4 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compta mandant</h1>
          <p className="text-sm text-gray-500 mt-0.5">Honoraires, reversements et compte rendu de gestion, par propriétaire</p>
        </div>
        <select
          value={year}
          onChange={e => setYear(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-fit"
        >
          {years.map(y => <option key={y} value={y}>Année {y}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-gray-400">Chargement…</div>
        ) : owners.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <Wallet size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucun propriétaire.</p>
          </div>
        ) : (
          owners.map(o => {
            const acc = data[`${o.id}:${year}`]
            const open = expandedId === o.id
            return (
              <div key={o.id} className="border-b border-gray-100 last:border-0">
                <button
                  onClick={() => toggle(o)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
                >
                  {open ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
                  <span className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                    <KeyRound size={15} className="text-blue-600" />
                  </span>
                  <span className="text-sm font-medium text-gray-900 flex-1">{o.full_name}</span>
                  {acc && (
                    <span className="text-xs text-gray-500 whitespace-nowrap">Solde à reverser : <strong className={acc.solde_a_reverser > 0 ? 'text-amber-700' : 'text-green-700'}>{fmtEuro(acc.solde_a_reverser)}</strong></span>
                  )}
                </button>
                {open && (
                  <div className="px-4 pb-4 pt-1 bg-blue-50/30">
                    {fetchingId === o.id || !acc
                      ? <p className="text-sm text-gray-400 py-2">Chargement des données…</p>
                      : <MandantDetail
                          owner={o}
                          acc={acc}
                          year={year}
                          downloading={downloadingId === o.id}
                          onDownload={() => downloadCrg(o)}
                          onReload={() => load(o.id)}
                        />}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

function MandantDetail({
  owner, acc, year, downloading, onDownload, onReload,
}: {
  owner: OwnerListItem
  acc: MandantAccount
  year: number
  downloading: boolean
  onDownload: () => void
  onReload: () => void
}) {
  const [adding, setAdding] = useState(false)
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('virement')
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [label, setLabel] = useState('')
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const h = acc.honoraires
  const stat = (label: string, value: string, color = 'text-gray-900') => (
    <div className="bg-white rounded-lg border border-gray-200 p-2 text-center">
      <p className={`text-base font-bold ${color}`}>{value}</p>
      <p className="text-[11px] text-gray-500">{label}</p>
    </div>
  )

  const submit = async () => {
    const n = parseFloat(amount.replace(',', '.'))
    if (!n || n <= 0) { toast.error('Saisissez un montant supérieur à 0.'); return }
    setSaving(true)
    try {
      await ownersApi.createReversement(owner.id, {
        period_year: year, amount: n, method, reversement_date: date, label: label || null,
      })
      toast.success('Reversement enregistré')
      setAdding(false); setAmount(''); setLabel('')
      await onReload()
    } catch (e) {
      toast.error(getErrorMessage(e, "Erreur lors de l'enregistrement du reversement"))
    } finally { setSaving(false) }
  }

  const remove = async (id: string) => {
    if (!window.confirm('Supprimer ce reversement ?')) return
    setDeletingId(id)
    try {
      await ownersApi.deleteReversement(owner.id, id)
      toast.success('Reversement supprimé')
      await onReload()
    } catch (e) {
      toast.error(getErrorMessage(e, 'Erreur lors de la suppression'))
    } finally { setDeletingId(null) }
  }

  return (
    <div className="max-w-2xl space-y-3">
      {/* Synthèse */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {stat('Total encaissé', fmtEuro(acc.total_encaisse))}
        {stat(`Honoraires (${h.rate}%)`, fmtEuro(h.ttc), 'text-orange-700')}
        {stat('Net propriétaire', fmtEuro(acc.net_proprietaire), 'text-blue-700')}
        {stat('Solde à reverser', fmtEuro(acc.solde_a_reverser), acc.solde_a_reverser > 0 ? 'text-amber-700' : 'text-green-700')}
      </div>

      {/* Détail du compte */}
      <div className="rounded-lg border border-gray-200 overflow-hidden text-sm">
        <div className="bg-gray-800 text-white px-3 py-1.5 text-xs font-semibold">COMPTE MANDANT {year}</div>
        <Row label="Loyers encaissés" value={fmtEuro(acc.loyers_encaisses)} />
        <Row label="Charges encaissées" value={fmtEuro(acc.charges_encaissees)} />
        <Row label="Total encaissé" value={fmtEuro(acc.total_encaisse)} strong />
        <Row label={`Honoraires HT (${h.rate}%)`} value={`− ${fmtEuro(h.ht)}`} />
        {h.vat_rate > 0 && <Row label={`TVA (${h.vat_rate}%)`} value={`− ${fmtEuro(h.vat)}`} />}
        <Row label="Net dû au propriétaire" value={fmtEuro(acc.net_proprietaire)} strong />
        <Row label="Déjà reversé" value={`− ${fmtEuro(acc.total_reverse)}`} />
        <Row label="Solde à reverser" value={fmtEuro(acc.solde_a_reverser)} strong />
      </div>

      {/* Reversements */}
      <div className="rounded-lg border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between bg-gray-50 px-3 py-1.5">
          <span className="text-xs font-semibold text-gray-700 uppercase">Reversements {year}</span>
          <button onClick={() => setAdding(v => !v)}
            className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700">
            <Plus size={13} /> Ajouter
          </button>
        </div>
        {adding && (
          <div className="px-3 py-3 bg-blue-50/40 grid grid-cols-1 sm:grid-cols-5 gap-2 items-end">
            <div className="sm:col-span-1">
              <label className="block text-[11px] text-gray-600 mb-1">Montant (€)</label>
              <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-[11px] text-gray-600 mb-1">Mode</label>
              <select value={method} onChange={e => setMethod(e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
                {Object.entries(METHOD_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-gray-600 mb-1">Date</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-[11px] text-gray-600 mb-1">Libellé (optionnel)</label>
              <div className="flex gap-2">
                <input value={label} onChange={e => setLabel(e.target.value)} placeholder="Ex. Reversement T1"
                  className="flex-1 px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
                <button onClick={submit} disabled={saving}
                  className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-60 whitespace-nowrap">
                  {saving ? '…' : 'Valider'}
                </button>
              </div>
            </div>
          </div>
        )}
        {acc.reversements.length === 0 ? (
          <p className="px-3 py-3 text-sm text-gray-400">Aucun reversement enregistré sur {year}.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {acc.reversements.map(r => (
                <tr key={r.id} className="border-t border-gray-100">
                  <td className="px-3 py-2 whitespace-nowrap">{new Date(r.reversement_date).toLocaleDateString('fr-FR')}</td>
                  <td className="px-3 py-2">{r.label || `Reversement ${year}`}</td>
                  <td className="px-3 py-2 text-gray-500">{r.method ? (METHOD_LABELS[r.method] || r.method) : '-'}</td>
                  <td className="px-3 py-2 text-right font-medium whitespace-nowrap">{fmtEuro(r.amount)}</td>
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => remove(r.id)} disabled={deletingId === r.id}
                      className="text-red-500 hover:text-red-700 disabled:opacity-50" title="Supprimer">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <button
        onClick={onDownload}
        disabled={downloading}
        className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {downloading ? <RefreshCw size={14} className="animate-spin" /> : <FileDown size={14} />}
        Télécharger le compte rendu de gestion (PDF)
      </button>
    </div>
  )
}

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between items-center gap-4 px-3 py-2 ${strong ? 'bg-gray-50 font-semibold' : 'border-b border-gray-100'}`}>
      <p className="text-sm text-gray-900">{label}</p>
      <p className="text-sm text-gray-900 whitespace-nowrap">{value}</p>
    </div>
  )
}
