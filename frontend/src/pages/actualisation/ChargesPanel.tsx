import { useState, useEffect, useCallback } from 'react'
import { KeyRound, RefreshCw, Calculator, CheckCircle2, Pencil, Trash2, X, FileDown, HeartHandshake } from 'lucide-react'
import { actualisationApi, type ChargeRow, type ChargePreview } from '@/api/actualisation'

const fmtEuro = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

const fmtDate = (s: string) => {
  const d = new Date(s + 'T00:00:00')
  return d.toLocaleDateString('fr-FR')
}

type FormState = {
  start: string
  end: string
  real: string
  newMonthly: string
  preview: ChargePreview | null
  editRegId?: string | null
}

export default function ChargesPanel({ flash }: { flash: (m: string) => void }) {
  const [rows, setRows] = useState<ChargeRow[]>([])
  const [loading, setLoading] = useState(true)
  const [forms, setForms] = useState<Record<string, FormState>>({})
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await actualisationApi.listCharges()
      setRows(r.data)
      // initialise les formulaires avec la période par défaut
      setForms(prev => {
        const next = { ...prev }
        for (const row of r.data) {
          if (!next[row.lease_id]) {
            next[row.lease_id] = {
              start: row.default_period_start,
              end: row.default_period_end,
              real: '',
              newMonthly: '',
              preview: null,
            }
          }
        }
        return next
      })
    } finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const upd = (id: string, patch: Partial<FormState>) =>
    setForms(p => ({ ...p, [id]: { ...p[id], ...patch } }))

  const preview = async (row: ChargeRow) => {
    const f = forms[row.lease_id]
    const real = parseFloat(f?.real)
    if (!f || !f.start || !f.end || isNaN(real)) return
    setBusyId(row.lease_id)
    try {
      const r = await actualisationApi.previewCharge(row.lease_id, {
        period_start: f.start, period_end: f.end, real_total: real,
      })
      upd(row.lease_id, {
        preview: r.data,
        newMonthly: f.newMonthly || String(r.data.suggested_monthly_provision),
      })
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors du calcul')
    } finally { setBusyId(null) }
  }

  const apply = async (row: ChargeRow) => {
    const f = forms[row.lease_id]
    const real = parseFloat(f?.real)
    const newMonthly = parseFloat(f?.newMonthly)
    if (!f || isNaN(real) || isNaN(newMonthly)) return
    const bal = f.preview?.balance ?? 0
    const soldeTxt = bal > 0 ? `remboursement de ${fmtEuro(bal)} au locataire`
      : bal < 0 ? `complément de ${fmtEuro(Math.abs(bal))} dû par le locataire`
      : 'aucun solde'
    const verb = f.editRegId ? 'Modifier' : 'Appliquer'
    if (!confirm(`${verb} la régularisation des charges de ${row.tenant_full_name} ?\n` +
      `Nouvelle provision mensuelle : ${fmtEuro(newMonthly)}\nSolde : ${soldeTxt}`)) return
    setBusyId(row.lease_id)
    try {
      const payload = {
        period_start: f.start, period_end: f.end, real_total: real,
        new_monthly_provision: newMonthly,
      }
      if (f.editRegId) {
        await actualisationApi.updateCharge(f.editRegId, payload)
        flash(`Régularisation des charges modifiée pour ${row.tenant_full_name}.`)
      } else {
        await actualisationApi.applyCharge(row.lease_id, payload)
        flash(`Régularisation des charges appliquée pour ${row.tenant_full_name}.`)
      }
      upd(row.lease_id, { preview: null, real: '', newMonthly: '', editRegId: null })
      load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la régularisation')
    } finally { setBusyId(null) }
  }

  const startEditRegul = (row: ChargeRow) => {
    const r = row.last_regularization
    if (!r) return
    upd(row.lease_id, {
      start: r.period_start, end: r.period_end,
      real: String(r.real_total), newMonthly: String(r.new_monthly_provision),
      preview: null, editRegId: r.id,
    })
  }

  const cancelEdit = (row: ChargeRow) =>
    upd(row.lease_id, {
      start: row.default_period_start, end: row.default_period_end,
      real: '', newMonthly: '', preview: null, editRegId: null,
    })

  const delRegul = async (row: ChargeRow) => {
    const r = row.last_regularization
    if (!r) return
    if (!confirm(`Supprimer cette régularisation de charges de ${row.tenant_full_name} ?\n` +
      `La provision mensuelle reviendra à ${fmtEuro(row.last_regularization?.new_monthly_provision ?? 0)} → valeur antérieure.`)) return
    setBusyId(row.lease_id)
    try {
      await actualisationApi.deleteCharge(r.id)
      flash(`Régularisation supprimée pour ${row.tenant_full_name}.`)
      upd(row.lease_id, { preview: null, real: '', newMonthly: '', editRegId: null })
      load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la suppression')
    } finally { setBusyId(null) }
  }

  const downloadRegul = async (row: ChargeRow) => {
    const r = row.last_regularization
    if (!r) return
    setBusyId(row.lease_id)
    try {
      await actualisationApi.downloadRegularizationPdf(
        r.id, `regularisation_charges_${row.tenant_full_name}.pdf`)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Téléchargement du PDF impossible')
    } finally { setBusyId(null) }
  }

  const amiableProvision = async (r: ChargeRow) => {
    const input = window.prompt(
      `Réévaluation amiable de la provision pour charges de ${r.tenant_full_name} (actuelle ${fmtEuro(r.current_monthly_provision)}).\nNouvelle provision mensuelle convenue (€) :`,
      String(r.current_monthly_provision))
    if (input == null) return
    const val = parseFloat(input.replace(',', '.'))
    if (isNaN(val) || val < 0) { alert('Montant invalide'); return }
    const note = window.prompt("Référence / note de l'accord (facultatif) :") ?? ''
    setBusyId(r.lease_id)
    try {
      await actualisationApi.amiableProvision(r.lease_id, { new_provision: val, note: note.trim() || undefined })
      flash(`Provision réévaluée d'un commun accord pour ${r.tenant_full_name}.`)
      load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la réévaluation')
    } finally { setBusyId(null) }
  }

  const groups = rows.reduce<Record<string, ChargeRow[]>>((acc, r) => {
    (acc[r.owner_name] ||= []).push(r); return acc
  }, {})

  if (loading) {
    return <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-sm text-gray-400">Chargement…</div>
  }
  if (rows.length === 0) {
    return <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">Aucun bail actif.</div>
  }

  return (
    <div className="space-y-5">
      {Object.entries(groups).map(([owner, list]) => (
        <div key={owner} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3 bg-gray-50 border-b border-gray-100">
            <KeyRound size={15} className="text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-900">{owner}</h3>
            <span className="text-xs text-gray-400">· {list.length} bail{list.length > 1 ? 'x' : ''}</span>
          </div>
          <div className="divide-y divide-gray-100">
            {list.map(r => {
              const f = forms[r.lease_id]
              const bal = f?.preview?.balance
              return (
                <div key={r.lease_id} className="px-5 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{r.tenant_full_name}</p>
                      <p className="text-xs text-gray-500">
                        {r.property_name} · Provision mensuelle actuelle {fmtEuro(r.current_monthly_provision)}
                      </p>
                      <button
                        onClick={() => amiableProvision(r)}
                        disabled={busyId === r.lease_id}
                        className="inline-flex items-center gap-1.5 mt-1.5 px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg hover:bg-emerald-100 disabled:opacity-40"
                        title="Fixer une provision convenue d'un commun accord (hors régularisation)">
                        <HeartHandshake size={13} /> Réévaluation amiable
                      </button>
                    </div>
                    {r.last_regularization && (
                      <div className="text-xs text-gray-400 text-right flex items-center gap-1.5">
                        <span>
                          Dernière régul. {r.last_regularization.applied_at ? fmtDate(r.last_regularization.applied_at.slice(0, 10)) : ''} ·
                          nouvelle provision {fmtEuro(r.last_regularization.new_monthly_provision)}
                        </span>
                        <button onClick={() => downloadRegul(r)} disabled={busyId === r.lease_id}
                          title="Télécharger le PDF de régularisation"
                          className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 disabled:opacity-50">
                          <FileDown size={13} />
                        </button>
                        <button onClick={() => startEditRegul(r)} disabled={busyId === r.lease_id}
                          title="Modifier cette régularisation"
                          className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-blue-600 disabled:opacity-50">
                          <Pencil size={13} />
                        </button>
                        <button onClick={() => delRegul(r)} disabled={busyId === r.lease_id}
                          title="Supprimer cette régularisation"
                          className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 disabled:opacity-50">
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )}
                  </div>

                  {f?.editRegId && (
                    <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-blue-50 text-blue-700 text-xs border border-blue-200">
                      Modification de la régularisation existante
                      <button onClick={() => cancelEdit(r)} title="Annuler" className="p-0.5 rounded hover:bg-white/70">
                        <X size={12} />
                      </button>
                    </div>
                  )}

                  {/* Formulaire de régularisation */}
                  {f && (
                    <div className="mt-2 flex flex-wrap items-end gap-2">
                      <div>
                        <label className="block text-[11px] text-gray-500 mb-0.5">Du</label>
                        <input type="date" value={f.start} onChange={e => upd(r.lease_id, { start: e.target.value, preview: null })}
                          className="px-2 py-1 border border-gray-300 rounded-lg text-sm" />
                      </div>
                      <div>
                        <label className="block text-[11px] text-gray-500 mb-0.5">Au</label>
                        <input type="date" value={f.end} onChange={e => upd(r.lease_id, { end: e.target.value, preview: null })}
                          className="px-2 py-1 border border-gray-300 rounded-lg text-sm" />
                      </div>
                      <div>
                        <label className="block text-[11px] text-gray-500 mb-0.5">Charges réelles (total)</label>
                        <input type="number" step="0.01" value={f.real}
                          onChange={e => upd(r.lease_id, { real: e.target.value, preview: null })}
                          placeholder="ex. 720.00" className="w-32 px-2 py-1 border border-gray-300 rounded-lg text-sm" />
                      </div>
                      <button onClick={() => preview(r)} disabled={busyId === r.lease_id || !f.real}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:opacity-50">
                        {busyId === r.lease_id ? <RefreshCw size={14} className="animate-spin" /> : <Calculator size={14} />}
                        Calculer
                      </button>
                    </div>
                  )}

                  {/* Résultat du calcul / édition */}
                  {(f?.preview || f?.editRegId) && (
                    <div className="mt-2 p-3 rounded-lg bg-gray-50 border border-gray-100 text-sm">
                      {f.preview ? (
                        <>
                          <p className="text-gray-600">
                            Sur {f.preview.months_count} mois : provisions versées <strong>{fmtEuro(f.preview.provisions_total)}</strong> ·
                            charges réelles <strong>{fmtEuro(f.preview.real_total)}</strong>
                          </p>
                          <p className="mt-1">
                            {bal != null && bal > 0 && <span className="text-green-700 font-semibold">Trop-perçu : {fmtEuro(bal)} → remboursé au locataire (déduit des prochains loyers)</span>}
                            {bal != null && bal < 0 && <span className="text-red-700 font-semibold">Complément dû par le locataire : {fmtEuro(Math.abs(bal))}</span>}
                            {bal != null && bal === 0 && <span className="text-gray-700 font-semibold">Provisions équilibrées (aucun solde)</span>}
                          </p>
                        </>
                      ) : (
                        <p className="text-gray-500 text-xs">Modifiez la période, les charges réelles ou la provision, puis enregistrez (« Calculer » pour recalculer le solde).</p>
                      )}
                      <div className="mt-2 flex flex-wrap items-end gap-2">
                        <div>
                          <label className="block text-[11px] text-gray-500 mb-0.5">Nouvelle provision mensuelle</label>
                          <input type="number" step="0.01" value={f.newMonthly}
                            onChange={e => upd(r.lease_id, { newMonthly: e.target.value })}
                            className="w-32 px-2 py-1 border border-gray-300 rounded-lg text-sm" />
                          {f.preview && <span className="ml-2 text-xs text-gray-400">suggérée {fmtEuro(f.preview.suggested_monthly_provision)}</span>}
                        </div>
                        <button onClick={() => apply(r)} disabled={busyId === r.lease_id || !f.newMonthly}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-40">
                          {busyId === r.lease_id ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                          {f.editRegId ? 'Enregistrer les modifications' : 'Appliquer la régularisation'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
