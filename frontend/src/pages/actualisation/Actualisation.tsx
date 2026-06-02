import { useState, useEffect, useCallback } from 'react'
import { TrendingUp, RefreshCw, Plus, CheckCircle2, KeyRound, ChevronDown, ChevronUp, Receipt, Pencil, Trash2, X, FileDown, Landmark } from 'lucide-react'
import { actualisationApi, type IrlIndexItem, type RevisionRow } from '@/api/actualisation'
import ChargesPanel from './ChargesPanel'

const fmtEuro = (n: number | null) =>
  n == null ? '—' : n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

export default function Actualisation() {
  const now = new Date()
  const [irl, setIrl] = useState<IrlIndexItem[]>([])
  const [rows, setRows] = useState<RevisionRow[]>([])
  const [loading, setLoading] = useState(true)
  const [showIrl, setShowIrl] = useState(false)
  const [tab, setTab] = useState<'loyers' | 'charges' | 'taxes'>('loyers')
  // form taxes foncières par bail : { year, amount }
  const [taxForm, setTaxForm] = useState<Record<string, { year: number; amount: string }>>({})
  const [msg, setMsg] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  // form IRL
  const [iy, setIy] = useState(now.getFullYear())
  const [iq, setIq] = useState(1)
  const [iv, setIv] = useState('')
  const [editId, setEditId] = useState<string | null>(null)
  // form référence par bail
  const [refForm, setRefForm] = useState<Record<string, { q: number; base: string }>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [a, b] = await Promise.all([actualisationApi.listIrl(), actualisationApi.listRevisions()])
      setIrl(a.data)
      setRows(b.data)
    } finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(''), 4000) }

  const resetIrlForm = () => { setEditId(null); setIv(''); setIq(1); setIy(now.getFullYear()) }

  const addIrl = async () => {
    const v = parseFloat(iv)
    if (!iy || !iq || !v) return
    try {
      if (editId) {
        await actualisationApi.updateIrl(editId, { year: iy, quarter: iq, value: v })
        flash(`Indice IRL T${iq} ${iy} modifié.`)
      } else {
        await actualisationApi.addIrl({ year: iy, quarter: iq, value: v })
        flash(`Indice IRL T${iq} ${iy} enregistré.`)
      }
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de l\'enregistrement de l\'indice')
      return
    }
    resetIrlForm()
    const a = await actualisationApi.listIrl(); setIrl(a.data)
    load()
  }

  const startEditIrl = (i: IrlIndexItem) => {
    setEditId(i.id); setIy(i.year); setIq(i.quarter); setIv(String(i.value)); setShowIrl(true)
  }

  const deleteIrl = async (i: IrlIndexItem) => {
    if (!confirm(`Supprimer l'indice IRL T${i.quarter} ${i.year} (${i.value}) ?`)) return
    try {
      await actualisationApi.deleteIrl(i.id)
      if (editId === i.id) resetIrlForm()
      flash(`Indice IRL T${i.quarter} ${i.year} supprimé.`)
      const a = await actualisationApi.listIrl(); setIrl(a.data)
      load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la suppression')
    }
  }

  const refreshInsee = async () => {
    const r = await actualisationApi.refreshIrl()
    flash(r.data.message)
    const a = await actualisationApi.listIrl(); setIrl(a.data)
    load()
  }

  const saveRef = async (r: RevisionRow) => {
    const f = refForm[r.lease_id]
    if (!f || !f.q || !f.base) return
    setBusyId(r.lease_id)
    try {
      await actualisationApi.setReference(r.lease_id, { irl_quarter: f.q, irl_base_index: parseFloat(f.base) })
      flash('Référence IRL enregistrée.')
      load()
    } finally { setBusyId(null) }
  }

  const apply = async (r: RevisionRow) => {
    if (!confirm(`Appliquer la révision du loyer de ${r.tenant_full_name} : ${fmtEuro(r.current_rent)} → ${fmtEuro(r.proposed_rent)} ?`)) return
    setBusyId(r.lease_id)
    try {
      await actualisationApi.applyRevision(r.lease_id)
      flash(`Loyer révisé pour ${r.tenant_full_name}.`)
      load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la révision')
    } finally { setBusyId(null) }
  }

  const downloadRevision = async (r: RevisionRow) => {
    setBusyId(r.lease_id)
    try {
      await actualisationApi.downloadRevisionPdf(r.lease_id, `revision_loyer_${r.tenant_full_name}.pdf`)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Téléchargement du PDF impossible')
    } finally { setBusyId(null) }
  }

  const downloadTaxes = async (r: RevisionRow) => {
    const f = taxForm[r.lease_id]
    const amount = parseFloat((f?.amount ?? '').replace(',', '.'))
    if (!f || isNaN(amount) || amount < 0) { alert('Saisissez un montant de taxe valide.'); return }
    setBusyId(r.lease_id)
    try {
      await actualisationApi.downloadTaxesPdf(
        { lease_id: r.lease_id, year: f.year, teom_amount: amount },
        `taxes_foncieres_${f.year}_${r.tenant_full_name}.pdf`)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Téléchargement du PDF impossible')
    } finally { setBusyId(null) }
  }

  // Regroupement par propriétaire
  const groups = rows.reduce<Record<string, RevisionRow[]>>((acc, r) => {
    (acc[r.owner_name] ||= []).push(r); return acc
  }, {})

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Actualisation des loyers et charges</h1>
        <p className="text-sm text-gray-500 mt-0.5">Révision annuelle du loyer (IRL) et régularisation des charges</p>
      </div>

      {/* Onglets */}
      <div className="flex gap-1 mb-5 border-b border-gray-200">
        <button onClick={() => setTab('loyers')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === 'loyers' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
          <TrendingUp size={15} /> Révision des loyers
        </button>
        <button onClick={() => setTab('charges')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === 'charges' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
          <Receipt size={15} /> Régularisation des charges
        </button>
        <button onClick={() => setTab('taxes')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === 'taxes' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
          <Landmark size={15} /> Taxes foncières
        </button>
      </div>

      {msg && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-green-50 text-green-800 text-sm border border-green-200 flex items-center gap-2">
          <CheckCircle2 size={15} className="text-green-600 shrink-0" /> {msg}
        </div>
      )}

      {tab === 'charges' && <ChargesPanel flash={flash} />}

      {tab === 'taxes' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b bg-gray-50">
            <p className="text-sm text-gray-600">
              Décompte de taxes foncières (TEOM) récupérable au prorata de l'occupation.
              Saisissez l'année et le montant total de la taxe récupérable, puis téléchargez le décompte.
            </p>
          </div>
          {loading ? (
            <div className="p-6 text-sm text-gray-400">Chargement…</div>
          ) : rows.length === 0 ? (
            <div className="p-6 text-sm text-gray-400">Aucun bail actif.</div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {rows.map(r => {
                const f = taxForm[r.lease_id] ?? { year: now.getFullYear(), amount: '' }
                return (
                  <li key={r.lease_id} className="px-5 py-3 flex flex-wrap items-end justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{r.tenant_full_name}</p>
                      <p className="text-xs text-gray-500 truncate">{r.property_name}</p>
                    </div>
                    <div className="flex items-end gap-2">
                      <div>
                        <label className="block text-[11px] text-gray-500 mb-0.5">Année</label>
                        <input type="number" value={f.year}
                          onChange={e => setTaxForm(p => ({ ...p, [r.lease_id]: { year: Number(e.target.value), amount: f.amount } }))}
                          className="w-24 px-2 py-1 border border-gray-300 rounded-lg text-sm" />
                      </div>
                      <div>
                        <label className="block text-[11px] text-gray-500 mb-0.5">Montant TEOM (€)</label>
                        <input type="text" value={f.amount} placeholder="178,00"
                          onChange={e => setTaxForm(p => ({ ...p, [r.lease_id]: { year: f.year, amount: e.target.value } }))}
                          className="w-32 px-2 py-1 border border-gray-300 rounded-lg text-sm" />
                      </div>
                      <button onClick={() => downloadTaxes(r)} disabled={busyId === r.lease_id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-40">
                        {busyId === r.lease_id ? <RefreshCw size={14} className="animate-spin" /> : <FileDown size={14} />} PDF
                      </button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}

      {tab === 'loyers' && (<>
      {/* Indices IRL */}
      <div className="bg-white rounded-xl border border-gray-200 mb-6">
        <button onClick={() => setShowIrl(v => !v)} className="w-full flex items-center justify-between px-5 py-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={18} className="text-blue-600" />
            <h2 className="font-semibold text-gray-900">Indices IRL ({irl.length})</h2>
          </div>
          {showIrl ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
        </button>
        {showIrl && (
          <div className="px-5 pb-5 border-t border-gray-100 pt-4">
            <div className="flex flex-wrap items-end gap-2 mb-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Année</label>
                <input type="number" value={iy} onChange={e => setIy(Number(e.target.value))} className="w-24 px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Trimestre</label>
                <select value={iq} onChange={e => setIq(Number(e.target.value))} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
                  {[1, 2, 3, 4].map(q => <option key={q} value={q}>T{q}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Valeur</label>
                <input type="number" step="0.01" value={iv} onChange={e => setIv(e.target.value)} placeholder="ex. 145.47" className="w-28 px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
              </div>
              <button onClick={addIrl} className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
                {editId ? <><CheckCircle2 size={14} /> Enregistrer</> : <><Plus size={14} /> Ajouter</>}
              </button>
              {editId && (
                <button onClick={resetIrlForm} className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">
                  <X size={14} /> Annuler
                </button>
              )}
              <button onClick={refreshInsee} className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">
                <RefreshCw size={14} /> Récupérer depuis l'INSEE
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {irl.length === 0 ? <p className="text-sm text-gray-400">Aucun indice. Ajoutez-en ou récupérez depuis l'INSEE.</p>
                : irl.map(i => (
                  <span key={i.id} className={`group inline-flex items-center gap-1.5 text-xs rounded-full pl-2.5 pr-1.5 py-1 ${editId === i.id ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'}`}>
                    T{i.quarter} {i.year} : <strong>{i.value}</strong>{i.source === 'insee' ? ' · INSEE' : ''}
                    <button onClick={() => startEditIrl(i)} title="Modifier" className="p-0.5 rounded hover:bg-white/70 text-gray-500 hover:text-blue-600">
                      <Pencil size={12} />
                    </button>
                    <button onClick={() => deleteIrl(i)} title="Supprimer" className="p-0.5 rounded hover:bg-white/70 text-gray-500 hover:text-red-600">
                      <Trash2 size={12} />
                    </button>
                  </span>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* Révisions par propriétaire */}
      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-sm text-gray-400">Chargement…</div>
      ) : rows.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">Aucun bail actif.</div>
      ) : (
        <div className="space-y-5">
          {Object.entries(groups).map(([owner, list]) => (
            <div key={owner} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-3 bg-gray-50 border-b border-gray-100">
                <KeyRound size={15} className="text-blue-600" />
                <h3 className="text-sm font-semibold text-gray-900">{owner}</h3>
                <span className="text-xs text-gray-400">· {list.length} bail{list.length > 1 ? 'x' : ''}</span>
              </div>
              <div className="divide-y divide-gray-100">
                {list.map(r => (
                  <div key={r.lease_id} className="px-5 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{r.tenant_full_name}</p>
                        <p className="text-xs text-gray-500">{r.property_name} · Loyer actuel {fmtEuro(r.current_rent)}
                          {r.revision_due && <span className="ml-2 text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">Révision due</span>}
                        </p>
                      </div>
                      <div className="text-right">
                        {r.irl_quarter && r.base_index != null ? (
                          <>
                            <p className="text-xs text-gray-500">
                              IRL réf. T{r.irl_quarter} = {r.base_index}
                              {r.latest_index_value != null ? ` → T${r.irl_quarter} ${r.latest_index_year} = ${r.latest_index_value}` : ' · indice récent manquant'}
                            </p>
                            {r.proposed_rent != null && (
                              <p className="text-sm font-semibold text-gray-900">Nouveau loyer : <span className="text-green-700">{fmtEuro(r.proposed_rent)}</span></p>
                            )}
                          </>
                        ) : (
                          <span className="text-xs text-gray-400">Référence IRL à définir</span>
                        )}
                      </div>
                    </div>

                    {/* Action */}
                    <div className="mt-2">
                      {r.irl_quarter && r.base_index != null ? (
                        <>
                        <button
                          onClick={() => apply(r)}
                          disabled={r.proposed_rent == null || busyId === r.lease_id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-40"
                          title={r.proposed_rent == null ? 'Indice IRL récent manquant pour ce trimestre' : ''}
                        >
                          {busyId === r.lease_id ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                          Appliquer la révision
                        </button>
                        <button
                          onClick={() => downloadRevision(r)}
                          disabled={busyId === r.lease_id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 ml-2"
                          title="Télécharger le document de révision (PDF)">
                          <FileDown size={14} /> PDF
                        </button>
                        </>
                      ) : (
                        <div className="flex flex-wrap items-end gap-2">
                          <div>
                            <label className="block text-[11px] text-gray-500 mb-0.5">Trimestre réf.</label>
                            <select
                              value={refForm[r.lease_id]?.q ?? 1}
                              onChange={e => setRefForm(p => ({ ...p, [r.lease_id]: { q: Number(e.target.value), base: p[r.lease_id]?.base ?? '' } }))}
                              className="px-2 py-1 border border-gray-300 rounded-lg text-sm">
                              {[1, 2, 3, 4].map(q => <option key={q} value={q}>T{q}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-[11px] text-gray-500 mb-0.5">Indice IRL de référence</label>
                            <input type="number" step="0.01"
                              value={refForm[r.lease_id]?.base ?? ''}
                              onChange={e => setRefForm(p => ({ ...p, [r.lease_id]: { q: p[r.lease_id]?.q ?? 1, base: e.target.value } }))}
                              placeholder="ex. 143.46" className="w-28 px-2 py-1 border border-gray-300 rounded-lg text-sm" />
                          </div>
                          <button onClick={() => saveRef(r)} disabled={busyId === r.lease_id}
                            className="px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:opacity-50">
                            Enregistrer la référence
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400 mt-4">
        Le locataire est prévenu 1 mois à l'avance : une mention « révision de loyer à venir » apparaît
        automatiquement sur l'avis d'échéance et la quittance du mois précédent, accompagnée d'une notification
        (l'e-mail s'activera avec la configuration SMTP).
      </p>
      </>)}
    </div>
  )
}
