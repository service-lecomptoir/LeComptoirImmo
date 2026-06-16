import { useState, useEffect, useMemo } from 'react'
import { BRAND } from '@/lib/brand'
import { Button } from '@/components/ui'
import { ShieldCheck, X, Plus, Trash2, TrendingUp, AlertTriangle, KeyRound, ChevronRight, ChevronDown, Sparkles } from 'lucide-react'
import { apiClient } from '@/api/client'
import {
  scoringApi, GRADE_COLORS,
  type ScoringRow, type ScoringDetail, type EventKind, type RelationEvent,
} from '@/api/scoring'
import { useAuthStore } from '@/store/authStore'

const POLARITY_STYLE: Record<string, { color: string; bg: string }> = {
  positif: { color: BRAND.teal, bg: '#D1FAE5' },
  negatif: { color: '#DC2626', bg: '#FEE2E2' },
  neutre:  { color: '#6B7280', bg: '#F3F4F6' },
}

function GradeBadge({ grade, score }: { grade: string; score: number }) {
  const c = GRADE_COLORS[grade] ?? GRADE_COLORS.C
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-sm font-bold whitespace-nowrap"
      style={{ color: c.color, background: c.bg }}>
      {grade} · {score}
    </span>
  )
}

function ScoreBar({ value }: { value: number }) {
  const c = value >= 70 ? BRAND.teal : value >= 55 ? '#D97706' : value >= 40 ? '#EA580C' : '#DC2626'
  return (
    <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${value}%`, background: c }} />
    </div>
  )
}

// ── Panneau de détail ──────────────────────────────────────────────────────
function DetailPanel({ tenantId, onClose, onChanged }: { tenantId: string; onClose: () => void; onChanged: () => void }) {
  const [detail, setDetail] = useState<ScoringDetail | null>(null)
  const [kinds, setKinds] = useState<EventKind[]>([])
  const [form, setForm] = useState({ kind: '', note: '', event_date: '' })
  const [saving, setSaving] = useState(false)
  const [ai, setAi] = useState<{ loading: boolean; text: string | null; disabled: boolean }>({ loading: false, text: null, disabled: false })

  const runAi = async () => {
    setAi({ loading: true, text: null, disabled: false })
    try {
      const { data } = await apiClient.get(`/scoring/${tenantId}/analysis`)
      setAi({ loading: false, text: data.analysis || null, disabled: data.enabled === false })
    } catch {
      setAi({ loading: false, text: null, disabled: false })
    }
  }

  const load = () => { scoringApi.detail(tenantId).then(r => setDetail(r.data)).catch(() => {}) }
  useEffect(() => { load(); scoringApi.eventKinds().then(r => setKinds(r.data)).catch(() => {}) }, [tenantId])

  const addEvent = async () => {
    if (!detail?.lease_id || !form.kind) return
    setSaving(true)
    try {
      await scoringApi.addEvent(detail.lease_id, { kind: form.kind, note: form.note || undefined, event_date: form.event_date || undefined })
      setForm({ kind: '', note: '', event_date: '' })
      load(); onChanged()
    } finally { setSaving(false) }
  }
  const delEvent = async (e: RelationEvent) => {
    if (!detail?.lease_id) return
    await scoringApi.deleteEvent(detail.lease_id, e.id)
    load(); onChanged()
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={onClose}>
      <div className="w-full max-w-xl bg-gray-50 h-full overflow-y-auto" onClick={e => e.stopPropagation()}>
        {!detail ? (
          <div className="p-8 text-gray-400">Chargement…</div>
        ) : (
          <div className="p-5 sm:p-6 space-y-5">
            {/* En-tête */}
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold text-gray-900">{detail.tenant_name}</h2>
                {detail.property_label && <p className="text-sm text-gray-500 whitespace-pre-line">{detail.property_label}</p>}
              </div>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-500"><X size={18} /></button>
            </div>

            {/* Score + stratégie */}
            <div className="bg-white rounded-xl border p-4 flex items-center gap-4">
              <GradeBadge grade={detail.grade} score={detail.score} />
              <p className="text-sm text-gray-700 flex-1">{detail.strategy}</p>
            </div>

            {/* Analyse IA (aide à la décision) */}
            <div className="bg-white rounded-xl border p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2"><Sparkles size={15} className="text-violet-600" /> Analyse IA</h3>
                <button onClick={runAi} disabled={ai.loading}
                  className="text-xs px-3 py-1.5 rounded-lg bg-violet-50 text-violet-700 hover:bg-violet-100 disabled:opacity-50 whitespace-nowrap">
                  {ai.loading ? 'Analyse…' : ai.text ? 'Réactualiser' : 'Analyser ce dossier'}
                </button>
              </div>
              {ai.disabled
                ? <p className="text-sm text-gray-400">L'assistant IA n'est pas activé sur la plateforme.</p>
                : ai.text
                  ? <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">{ai.text}</p>
                  : <p className="text-sm text-gray-400">Lecture contextuelle du dossier : forces, points de vigilance et recommandation d'action.</p>}
            </div>

            {/* Facteurs */}
            <div className="bg-white rounded-xl border p-4">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2"><TrendingUp size={15} className="text-blue-600" /> Facteurs</h3>
              <div className="space-y-3">
                {detail.factors.map(f => (
                  <div key={f.key}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="font-medium text-gray-800">{f.label} <span className="text-gray-400 text-xs">· {f.weight}%</span></span>
                      <span className="font-semibold text-gray-900">{f.score}/100</span>
                    </div>
                    <ScoreBar value={f.score} />
                    <p className="text-xs text-gray-500 mt-1">{f.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Relation locataire */}
            <div className="bg-white rounded-xl border p-4">
              <h3 className="font-semibold text-gray-900 mb-3">Relation locataire</h3>
              {!detail.lease_id ? (
                <p className="text-sm text-gray-400">Aucun contrat actif. La liste de relation se gère sur un contrat.</p>
              ) : (
                <>
                  <div className="flex flex-col sm:flex-row gap-2 mb-3">
                    <select value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value }))}
                      className="border border-gray-200 rounded-lg px-2 py-2 text-sm sm:w-52">
                      <option value="">Type d'événement…</option>
                      <optgroup label="Positif">
                        {kinds.filter(k => k.polarity === 'positif').map(k => <option key={k.kind} value={k.kind}>{k.label}</option>)}
                      </optgroup>
                      <optgroup label="Négatif">
                        {kinds.filter(k => k.polarity === 'negatif').map(k => <option key={k.kind} value={k.kind}>{k.label}</option>)}
                      </optgroup>
                      <optgroup label="Neutre">
                        {kinds.filter(k => k.polarity === 'neutre').map(k => <option key={k.kind} value={k.kind}>{k.label}</option>)}
                      </optgroup>
                    </select>
                    <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                      placeholder="Note (facultatif)" className="border border-gray-200 rounded-lg px-3 py-2 text-sm flex-1" />
                    <Button variant="primary" onClick={addEvent} disabled={!form.kind || saving}
                      className="gap-1 font-semibold" leftIcon={<Plus size={15} />}>
                      Ajouter
                    </Button>
                  </div>
                  {detail.relationship_events.length === 0 ? (
                    <p className="text-sm text-gray-400">Aucun événement enregistré.</p>
                  ) : (
                    <ul className="space-y-2">
                      {detail.relationship_events.map(e => {
                        const ps = POLARITY_STYLE[e.polarity ?? 'neutre']
                        return (
                          <li key={e.id} className="flex items-start gap-2 text-sm">
                            <span className="text-xs font-medium px-2 py-0.5 rounded-full shrink-0" style={{ color: ps.color, background: ps.bg }}>{e.kind_label}</span>
                            <div className="flex-1 min-w-0">
                              {e.note && <p className="text-gray-800">{e.note}</p>}
                              <p className="text-xs text-gray-400">{e.date}{e.author_name ? ` · ${e.author_name}` : ''}</p>
                            </div>
                            <button onClick={() => delEvent(e)} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-red-500"><Trash2 size={13} /></button>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function ScoringList() {
  const [rows, setRows] = useState<ScoringRow[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  // Mandataire : regroupement par propriétaire (pliable). GP : liste à plat (un seul bailleur = lui).
  const isMandataire = useAuthStore(s => s.user?.role === 'gestionnaire')
  const [collapsedOwners, setCollapsedOwners] = useState<Set<string>>(new Set())
  const toggleOwner = (owner: string) =>
    setCollapsedOwners(prev => {
      const next = new Set(prev)
      next.has(owner) ? next.delete(owner) : next.add(owner)
      return next
    })

  const load = () => {
    setLoading(true)
    scoringApi.list().then(r => setRows(r.data.items)).catch(() => {}).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const atRisk = rows.filter(r => r.grade === 'D' || r.grade === 'E').length

  // Regroupement par propriétaire (bailleur) — utile au gestionnaire mandataire.
  const groups = useMemo(() => {
    const m = new Map<string, ScoringRow[]>()
    for (const r of rows) {
      const k = r.owner_name || 'Sans propriétaire'
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(r)
    }
    const arr = Array.from(m.entries()).map(([owner, items]) => ({
      owner,
      items: [...items].sort((a, b) => a.score - b.score),
      risk: items.filter(i => i.grade === 'D' || i.grade === 'E').length,
    }))
    // Groupes triés par pire score (priorité d'action)
    arr.sort((a, b) => (a.items[0]?.score ?? 100) - (b.items[0]?.score ?? 100))
    return arr
  }, [rows])

  const HEADERS = ['Score', 'Locataire', 'Bien', "Taux d'effort", 'Ponctualité', 'Impayés', 'Stratégie']

  const renderRows = (items: ScoringRow[]) => (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px]">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
            {HEADERS.map(h => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map(r => (
            <tr key={r.tenant_id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(r.tenant_id)}>
              <td className="px-4 py-3"><GradeBadge grade={r.grade} score={r.score} /></td>
              <td className="px-4 py-3"><p className="text-sm font-medium text-gray-900 whitespace-nowrap">{r.tenant_name}</p></td>
              <td className="px-4 py-3 text-sm text-gray-500 whitespace-pre-line">{r.property_label ?? '—'}</td>
              <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">{r.effort_rate != null ? `${Math.round(r.effort_rate * 100)}%` : '—'}</td>
              <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">{r.on_time_rate != null ? `${Math.round(r.on_time_rate * 100)}%` : '—'}</td>
              <td className="px-4 py-3 text-sm">
                {r.overdue_count > 0
                  ? <span className="text-red-600 font-medium whitespace-nowrap">{r.overdue_count} · {r.outstanding.toLocaleString('fr-FR')} €</span>
                  : <span className="text-gray-400">—</span>}
              </td>
              <td className="px-4 py-3 text-xs text-gray-500 max-w-[240px]">{r.strategy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ShieldCheck size={22} className="text-blue-600" /> Scoring locataires
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Qualité de payeur calculée à partir des revenus, de l'historique de paiement et de la relation locataire.
        </p>
      </div>

      {atRisk > 0 && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm"
          style={{ background: '#FEF2F2', borderColor: '#FECACA', color: '#B91C1C' }}>
          <AlertTriangle size={16} />
          <span><b>{atRisk}</b> locataire{atRisk > 1 ? 's' : ''} à risque (note D ou E) : action recommandée.</span>
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-xl border py-12 text-center text-gray-400 text-sm">Chargement…</div>
      ) : rows.length === 0 ? (
        <div className="bg-white rounded-xl border py-12 text-center text-gray-400 text-sm">Aucun locataire à scorer.</div>
      ) : !isMandataire ? (
        // GP : liste à plat, sans rappel du propriétaire.
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {renderRows([...rows].sort((a, b) => a.score - b.score))}
        </div>
      ) : (
        // Mandataire : groupes par propriétaire, pliables/dépliables.
        <div className="space-y-5">
          {groups.map(g => {
            const open = !collapsedOwners.has(g.owner)
            return (
              <div key={g.owner} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => toggleOwner(g.owner)}
                  className="w-full flex items-center justify-between gap-2 px-4 py-3 border-b border-gray-100 bg-gray-50 text-left hover:bg-gray-100"
                >
                  <div className="flex items-center gap-2">
                    {open ? <ChevronDown size={15} className="text-gray-400 shrink-0" /> : <ChevronRight size={15} className="text-gray-400 shrink-0" />}
                    <KeyRound size={15} className="text-gray-500" />
                    <span className="text-sm font-semibold text-gray-900">{g.owner}</span>
                    <span className="text-xs text-gray-400">· {g.items.length} locataire{g.items.length > 1 ? 's' : ''}</span>
                  </div>
                  {g.risk > 0 && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ color: '#B91C1C', background: '#FEE2E2' }}>
                      {g.risk} à risque
                    </span>
                  )}
                </button>
                {open && renderRows(g.items)}
              </div>
            )
          })}
        </div>
      )}

      {selected && <DetailPanel tenantId={selected} onClose={() => setSelected(null)} onChanged={load} />}
    </div>
  )
}
