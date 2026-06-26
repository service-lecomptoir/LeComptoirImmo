import { useEffect, useMemo, useState } from 'react'
import { BRAND } from '@/lib/brand'
import { Button } from '@/components/ui'
import { useSearchParams, Link } from 'react-router-dom'
import { DoorOpen, Plus, X, Trash2, CheckCircle2, ArrowLeftRight, Wallet } from 'lucide-react'
import { leaseExitsApi, type LeaseExit, type Deduction } from '@/api/leaseExits'
import { leasesApi } from '@/api/leases'
import { InspectionForm } from '@/components/inspections/InspectionForm'
import { toast } from '@/store/toast'

const STATUS: Record<string, { label: string; cls: string; step: number }> = {
  preavis:        { label: 'Préavis',        cls: 'bg-blue-100 text-blue-700',     step: 0 },
  etat_des_lieux: { label: 'État des lieux', cls: 'bg-amber-100 text-amber-700',   step: 1 },
  decompte:       { label: 'Décompte',       cls: 'bg-violet-100 text-violet-700', step: 2 },
  cloture:        { label: 'Clôturé',        cls: 'bg-gray-200 text-gray-600',     step: 3 },
}
const STEPS = ['Préavis', 'État des lieux', 'Décompte', 'Clôture']

const COND_LABELS: Record<string, string> = {
  tres_bon: 'Très bon', bon: 'Bon', moyen: 'Moyen', mauvais: 'Mauvais',
}
const fmtDate = (d?: string | null) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—')
const eur = (n: number) => `${n.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`

interface ActiveLease { id: string; tenant_full_name?: string; property_name?: string }

export default function SortiesPage({ embedded = false }: { embedded?: boolean }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [exits, setExits] = useState<LeaseExit[]>([])
  const [selected, setSelected] = useState<LeaseExit | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [activeLeases, setActiveLeases] = useState<ActiveLease[]>([])
  const [createLease, setCreateLease] = useState('')
  const [newDeduction, setNewDeduction] = useState({ label: '', amount: '' })
  const [showSortieForm, setShowSortieForm] = useState(false)

  // Recharge le dossier sélectionné (après création d'un état des lieux de sortie,
  // pour que la liste des états des lieux du bail se mette à jour).
  const reloadSelected = async () => {
    if (!selected) return
    try {
      const r = await leaseExitsApi.byLease(selected.lease_id)
      if (r.data) refresh(r.data)
    } catch {
      /* */
    }
  }

  const load = async () => {
    setLoading(true)
    try {
      const r = await leaseExitsApi.list()
      setExits(r.data)
      return r.data
    } catch { return [] } finally { setLoading(false) }
  }

  useEffect(() => {
    (async () => {
      const list = await load()
      const leaseParam = searchParams.get('lease')
      if (leaseParam) {
        const existing = list.find(e => e.lease_id === leaseParam)
        if (existing) setSelected(existing)
        else { setCreateLease(leaseParam); setShowCreate(true) }
        setSearchParams({}, { replace: true })
      }
    })()
  }, [])

  useEffect(() => {
    if (!showCreate) return
    leasesApi.list({ is_active: true, limit: 200 }).then(r => {
      const items = (r.data as any).items ?? r.data
      setActiveLeases(items as ActiveLease[])
    }).catch(() => {})
  }, [showCreate])

  const exitLeaseIds = useMemo(() => new Set(exits.map(e => e.lease_id)), [exits])

  const refresh = (ex: LeaseExit) => {
    setSelected(ex)
    setExits(prev => prev.map(e => (e.id === ex.id ? ex : e)))
  }

  const patch = async (data: Parameters<typeof leaseExitsApi.update>[1]) => {
    if (!selected) return
    setBusy(true)
    try { refresh((await leaseExitsApi.update(selected.id, data)).data) }
    catch { /* */ } finally { setBusy(false) }
  }

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createLease) return
    setBusy(true)
    try {
      const r = await leaseExitsApi.create({ lease_id: createLease })
      toast.success('Dossier de sortie ouvert.')
      setShowCreate(false)
      setCreateLease('')
      await load()
      setSelected(r.data)
    } catch { /* */ } finally { setBusy(false) }
  }

  const close = async () => {
    if (!selected) return
    if (!window.confirm(
      `Clôturer la sortie de ${selected.tenant_name ?? 'ce locataire'} ?\n` +
      `Le bail sera résilié au ${fmtDate(selected.departure_date)} et le bien remis en location.\n` +
      `Dépôt à restituer : ${eur(selected.deposit_to_return)}.`
    )) return
    setBusy(true)
    try {
      refresh((await leaseExitsApi.close(selected.id)).data)
      toast.success('Dossier clôturé : bail résilié.')
    } catch { /* */ } finally { setBusy(false) }
  }

  const removeExit = async () => {
    if (!selected) return
    if (!window.confirm('Supprimer ce dossier de sortie ? (le bail reste actif)')) return
    try {
      await leaseExitsApi.remove(selected.id)
      setSelected(null)
      await load()
    } catch { /* */ }
  }

  const addDeduction = () => {
    if (!selected || !newDeduction.label.trim() || !newDeduction.amount) return
    const next: Deduction[] = [
      ...selected.deductions,
      { label: newDeduction.label.trim(), amount: Number(newDeduction.amount) },
    ]
    setNewDeduction({ label: '', amount: '' })
    patch({ deductions: next })
  }

  const removeDeduction = (idx: number) => {
    if (!selected) return
    patch({ deductions: selected.deductions.filter((_, i) => i !== idx) })
  }

  const closed = selected?.status === 'cloture'
  const entries = selected?.lease_inspections.filter(i => i.inspection_type === 'entree') ?? []
  const sorties = selected?.lease_inspections.filter(i => i.inspection_type === 'sortie') ?? []

  return (
    <div className={embedded ? '' : 'p-4 sm:p-6'}>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {!embedded ? (
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><DoorOpen size={22} /> Sortie du locataire</h1>
            <p className="text-gray-500 text-sm mt-1">
              Préavis, état des lieux de sortie, comparaison avec l'entrée, décompte du dépôt de garantie et clôture du dossier.
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            Processus de <strong>départ</strong> : préavis, état des lieux de sortie, comparaison avec l'entrée,
            décompte du dépôt de garantie et clôture du dossier.
          </p>
        )}
        <Button variant="primary" onClick={() => setShowCreate(true)}
          className="rounded-xl font-semibold self-start" leftIcon={<Plus size={16} />}>
          Nouvelle sortie
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Liste */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
          ) : exits.length === 0 ? (
            <div className="py-12 text-center">
              <DoorOpen size={32} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm text-gray-400">Aucun dossier de sortie</p>
              <p className="text-xs text-gray-400 mt-1">Ouvrez-en un dès réception d'un préavis.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {exits.map(ex => {
                const st = STATUS[ex.status] ?? STATUS.preavis
                return (
                  <li key={ex.id}>
                    <button onClick={() => setSelected(ex)}
                      className={`w-full text-left px-4 py-3.5 hover:bg-gray-50 ${selected?.id === ex.id ? 'bg-blue-50' : ''}`}>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900 truncate">{ex.tenant_name ?? 'Locataire'}</p>
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${st.cls}`}>{st.label}</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">
                        {ex.property_name ?? 'Bien'} · départ {fmtDate(ex.departure_date)}
                      </p>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* Détail */}
        <div className="lg:col-span-2">
          {!selected ? (
            <div className="bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center h-64">
              <DoorOpen size={36} className="text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Sélectionnez un dossier de sortie</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{selected.tenant_name ?? 'Locataire'}</h2>
                  <p className="text-sm text-gray-500">
                    {selected.property_name ?? 'Bien'} · <Link to={`/leases/${selected.lease_id}`} className="text-blue-600 underline">voir le bail</Link>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${(STATUS[selected.status] ?? STATUS.preavis).cls}`}>
                    {(STATUS[selected.status] ?? STATUS.preavis).label}
                  </span>
                  {!closed && (
                    <button onClick={removeExit} className="p-1.5 text-red-400 hover:text-red-600" title="Supprimer le dossier">
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Étapes */}
              <div className="flex items-center gap-1">
                {STEPS.map((s, i) => {
                  const cur = (STATUS[selected.status] ?? STATUS.preavis).step
                  return (
                    <div key={s} className="flex-1 flex items-center gap-1">
                      <div className={`flex-1 text-center text-[11px] font-semibold rounded-lg py-1.5 ${i <= cur ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'}`}>{s}</div>
                      {i < STEPS.length - 1 && <div className={`w-3 h-0.5 ${i < cur ? 'bg-blue-600' : 'bg-gray-200'}`} />}
                    </div>
                  )
                })}
              </div>

              {/* Préavis & dates */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Préavis reçu le</label>
                  <input type="date" disabled={closed} value={selected.notice_received_at ?? ''}
                    onChange={e => patch({ notice_received_at: e.target.value || null })}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Date de départ prévue</label>
                  <input type="date" disabled={closed} value={selected.departure_date ?? ''}
                    onChange={e => patch({ departure_date: e.target.value || null })}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
                </div>
              </div>

              {/* États des lieux + comparaison */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                    <ArrowLeftRight size={15} /> États des lieux (entrée ↔ sortie)
                  </h3>
                  {!closed && !showSortieForm && (
                    <button
                      onClick={() => setShowSortieForm(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100"
                    >
                      <Plus size={13} /> État des lieux de sortie
                    </button>
                  )}
                </div>
                {showSortieForm && (
                  <InspectionForm
                    leaseId={selected.lease_id}
                    propertyId={selected.property_id}
                    lockedType="sortie"
                    onSaved={() => {
                      setShowSortieForm(false)
                      reloadSelected()
                      toast.success('État des lieux de sortie enregistré.')
                    }}
                    onCancel={() => setShowSortieForm(false)}
                  />
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {([['entry', 'Entrée', entries, selected.entry_inspection] as const,
                     ['exit', 'Sortie', sorties, selected.exit_inspection] as const]).map(([kind, label, opts, current]) => (
                    <div key={kind} className="rounded-lg border border-gray-200 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-xs font-semibold text-gray-700">{label}</p>
                        {!closed && (
                          <select value={current?.id ?? ''}
                            onChange={e => patch(kind === 'entry'
                              ? { entry_inspection_id: e.target.value || null }
                              : { exit_inspection_id: e.target.value || null })}
                            className="text-xs border border-gray-200 rounded px-2 py-1 max-w-[55%]">
                            <option value="">— Choisir —</option>
                            {opts.map(i => (
                              <option key={i.id} value={i.id}>{new Date(i.inspection_date).toLocaleDateString('fr-FR')}</option>
                            ))}
                          </select>
                        )}
                      </div>
                      {current ? (
                        <div className="text-sm space-y-1">
                          <p><span className="text-gray-400">Date :</span> {fmtDate(current.inspection_date)}</p>
                          <p><span className="text-gray-400">État général :</span> {current.overall_condition ? (COND_LABELS[current.overall_condition] ?? current.overall_condition) : '—'}</p>
                          {current.notes && <p className="text-xs text-gray-500 whitespace-pre-wrap line-clamp-4">{current.notes}</p>}
                        </div>
                      ) : (
                        <p className="text-xs text-gray-400">
                          Aucun état des lieux {label.toLowerCase()} relié.
                          {kind === 'exit' && !closed && <> Créez-le via « État des lieux de sortie » ci-dessus, puis sélectionnez-le ici.</>}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
                {selected.entry_inspection && selected.exit_inspection && (
                  <p className="text-xs mt-2 px-1 text-gray-500">
                    {selected.entry_inspection.overall_condition === selected.exit_inspection.overall_condition
                      ? '✅ État général identique entre l\'entrée et la sortie.'
                      : '⚠️ État général différent entre l\'entrée et la sortie : vérifiez les dégradations et ajustez les retenues ci-dessous.'}
                  </p>
                )}
              </div>

              {/* Dépôt de garantie */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                  <Wallet size={15} /> Dépôt de garantie
                </h3>
                <div className="rounded-lg border border-gray-200 p-3 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Dépôt versé</span>
                    <span className="font-medium text-gray-900">{eur(selected.deposit_amount)}</span>
                  </div>
                  {selected.deductions.map((d, i) => (
                    <div key={i} className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">− {d.label}</span>
                      <span className="flex items-center gap-2">
                        <span className="text-red-600">−{eur(d.amount)}</span>
                        {!closed && (
                          <button onClick={() => removeDeduction(i)} className="text-gray-300 hover:text-red-500"><X size={13} /></button>
                        )}
                      </span>
                    </div>
                  ))}
                  {!closed && (
                    <div className="flex gap-2 pt-1">
                      <input placeholder="Retenue (ex. dégradation mur salon)" value={newDeduction.label}
                        onChange={e => setNewDeduction(d => ({ ...d, label: e.target.value }))}
                        className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
                      <input type="number" min="0" step="0.01" placeholder="€" value={newDeduction.amount}
                        onChange={e => setNewDeduction(d => ({ ...d, amount: e.target.value }))}
                        className="w-24 border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
                      <button onClick={addDeduction} disabled={busy || !newDeduction.label.trim() || !newDeduction.amount}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-50">
                        Ajouter
                      </button>
                    </div>
                  )}
                  <div className="flex justify-between text-sm border-t border-gray-100 pt-2">
                    <span className="font-semibold text-gray-900">À restituer au locataire</span>
                    <span className="font-bold" style={{ color: BRAND.teal }}>{eur(selected.deposit_to_return)}</span>
                  </div>
                </div>
              </div>

              {/* Commentaires */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Commentaires</label>
                <textarea defaultValue={selected.comments ?? ''} rows={2} disabled={closed}
                  onBlur={e => { if ((selected.comments ?? '') !== e.target.value) patch({ comments: e.target.value || null }) }}
                  placeholder="Restitution des clés, relevés de compteurs, adresse de réexpédition…"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none disabled:bg-gray-50" />
              </div>

              {/* Avancement + clôture */}
              {!closed ? (
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  {selected.status === 'preavis' && (
                    <button onClick={() => patch({ status: 'etat_des_lieux' })} disabled={busy}
                      className="px-3 py-2 rounded-lg text-xs font-semibold bg-amber-100 hover:bg-amber-200 text-amber-800 disabled:opacity-50">
                      Passer à l'état des lieux
                    </button>
                  )}
                  {selected.status === 'etat_des_lieux' && (
                    <button onClick={() => patch({ status: 'decompte' })} disabled={busy}
                      className="px-3 py-2 rounded-lg text-xs font-semibold bg-violet-100 hover:bg-violet-200 text-violet-700 disabled:opacity-50">
                      Passer au décompte
                    </button>
                  )}
                  <Button variant="primary" onClick={close} disabled={busy || !selected.departure_date}
                    title={!selected.departure_date ? 'Renseignez la date de départ' : undefined}
                    className="ml-auto font-semibold"
                    leftIcon={<CheckCircle2 size={15} />}>
                    Clôturer (résilier le bail)
                  </Button>
                </div>
              ) : (
                <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 text-sm text-gray-600">
                  Dossier clôturé le {fmtDate(selected.closed_at)} : bail résilié, bien remis en location.
                  Dépôt restitué : <b>{eur(selected.deposit_to_return)}</b>
                  {selected.total_deductions > 0 && <> (retenues : {eur(selected.total_deductions)})</>}.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Modale création ── */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Nouvelle sortie de locataire</h3>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <form onSubmit={create} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bail concerné *</label>
                <select required value={createLease} onChange={e => setCreateLease(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                  <option value="">— Choisir un bail actif —</option>
                  {activeLeases.filter(l => !exitLeaseIds.has(l.id)).map(l => (
                    <option key={l.id} value={l.id}>
                      {[l.tenant_full_name, l.property_name].filter(Boolean).join(' : ') || l.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-400 mt-1">Le dépôt de garantie du bail est repris automatiquement ; l'état des lieux d'entrée est pré-relié s'il existe.</p>
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Annuler</button>
                <Button type="submit" variant="primary" disabled={busy || !createLease} isLoading={busy}
                  className="px-5 font-semibold">
                  {busy ? 'Ouverture…' : 'Ouvrir le dossier'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
