import { useEffect, useMemo, useState } from 'react'
import { formatPhoneDisplay } from '@/utils/format'
import { Users, Plus, Trash2, X, Scale, BadgeCheck, ShieldQuestion, FileCheck2 } from 'lucide-react'
import { candidaturesApi, type Candidature, type CandidatureStatus } from '@/api/candidatures'
import { propertiesApi } from '@/api/properties'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'

interface Prop { id: string; name: string }

const STATUS: Record<CandidatureStatus, { label: string; cls: string }> = {
  nouvelle: { label: 'Nouvelle',  cls: 'bg-blue-100 text-blue-700' },
  en_etude: { label: 'En étude',  cls: 'bg-amber-100 text-amber-700' },
  retenue:  { label: 'Retenue',   cls: 'bg-emerald-100 text-emerald-700' },
  refusee:  { label: 'Refusée',   cls: 'bg-gray-200 text-gray-600' },
}

const pct = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v * 100)} %`)

export default function CandidaturesPage() {
  const [items, setItems] = useState<Candidature[]>([])
  const [props, setProps] = useState<Prop[]>([])
  const [docLabels, setDocLabels] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [propertyId, setPropertyId] = useState('')
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState<Candidature | null>(null)
  const [showCompare, setShowCompare] = useState(false)
  const [compare, setCompare] = useState<{ rent_reference: number | null; candidates: Candidature[] } | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ property_id: '', first_name: '', last_name: '', email: '', phone: '', employment: '', monthly_income: '', has_guarantor: false, message: '' })
  const [busy, setBusy] = useState(false)
  // Propriétaire : accès en lecture seule (les écritures sont bloquées côté serveur).
  const readOnly = useAuthStore(s => s.user?.role === 'proprietaire')

  const load = async () => {
    setLoading(true)
    try {
      const [c, p] = await Promise.all([
        candidaturesApi.list({
          property_id: propertyId || undefined,
          status: status || undefined,
        }),
        propertiesApi.list({ limit: 200 }),
      ])
      setItems(c.data)
      setProps(((p.data as any).items ?? p.data) as Prop[])
    } catch { /* */ } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [propertyId, status])
  useEffect(() => {
    candidaturesApi.docKeys().then(r =>
      setDocLabels(Object.fromEntries(r.data.map(d => [d.key, d.label])))
    ).catch(() => {})
  }, [])

  const propName = useMemo(() => Object.fromEntries(props.map(p => [p.id, p.name])), [props])

  const patch = async (id: string, data: Parameters<typeof candidaturesApi.update>[1]) => {
    setBusy(true)
    try {
      const r = await candidaturesApi.update(id, data)
      setSelected(r.data)
      setItems(prev => prev.map(c => (c.id === id ? r.data : c)))
    } catch { /* */ } finally { setBusy(false) }
  }

  const toggleDoc = (c: Candidature, key: string, field: 'provided' | 'verified') => {
    const docs = c.docs.map(d => d.key === key ? { ...d, [field]: !d[field] } : d)
    patch(c.id, { docs })
  }

  const remove = async (c: Candidature) => {
    if (!window.confirm(`Supprimer la candidature de ${c.full_name} ?`)) return
    try {
      await candidaturesApi.remove(c.id)
      setSelected(null)
      await load()
    } catch { /* */ }
  }

  const openCompare = async (pid: string) => {
    try {
      const r = await candidaturesApi.compare(pid)
      setCompare(r.data)
      setShowCompare(true)
    } catch { /* */ }
  }

  const createManual = async (e: React.FormEvent) => {
    e.preventDefault()
    const fullName = `${form.first_name.trim()} ${form.last_name.trim()}`.trim()
    if (!form.property_id || !fullName) return
    setBusy(true)
    try {
      await candidaturesApi.create({
        property_id: form.property_id,
        full_name: fullName,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        employment: form.employment.trim() || null,
        monthly_income: form.monthly_income.trim() ? Number(form.monthly_income) : null,
        has_guarantor: form.has_guarantor,
        message: form.message.trim() || null,
      })
      toast.success('Candidature ajoutée.')
      setShowForm(false)
      setForm({ property_id: '', first_name: '', last_name: '', email: '', phone: '', employment: '', monthly_income: '', has_guarantor: false, message: '' })
      await load()
    } catch { /* */ } finally { setBusy(false) }
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><Users size={22} /> Candidatures</h1>
          <p className="text-gray-500 text-sm mt-1">
            Dossiers candidats centralisés : vérifiez les pièces, comparez les profils et sélectionnez le locataire le plus adapté.
          </p>
        </div>
        {readOnly ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-500 bg-gray-100 self-start">
            Lecture seule
          </span>
        ) : (
          <button onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white self-start"
            style={{ background: '#0D2F5C' }}>
            <Plus size={16} /> Ajouter un dossier
          </button>
        )}
      </div>

      {/* Filtres */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select value={propertyId} onChange={e => setPropertyId(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Tous les biens</option>
          {props.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Tous les statuts</option>
          {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        {propertyId && (
          <button onClick={() => openCompare(propertyId)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold bg-violet-100 hover:bg-violet-200 text-violet-700">
            <Scale size={15} /> Comparer les profils
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Liste */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center">
              <Users size={32} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm text-gray-400">Aucune candidature</p>
              <p className="text-xs text-gray-400 mt-1">Les dossiers déposés depuis vos annonces publiées arrivent ici.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {items.map(c => {
                const st = STATUS[c.status] ?? STATUS.nouvelle
                return (
                  <li key={c.id}>
                    <button onClick={() => setSelected(c)}
                      className={`w-full text-left px-4 py-3.5 hover:bg-gray-50 ${selected?.id === c.id ? 'bg-blue-50' : ''}`}>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900 truncate">{c.full_name}</p>
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${st.cls}`}>{st.label}</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{propName[c.property_id] ?? 'Bien'} · score {c.metrics.score}/100</p>
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
              <FileCheck2 size={36} className="text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Sélectionnez un dossier pour le vérifier et l'évaluer</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{selected.full_name}</h2>
                  <p className="text-sm text-gray-500">
                    {propName[selected.property_id] ?? 'Bien'} · {selected.source === 'annonce' ? "via l'annonce publique" : 'saisie manuelle'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${(STATUS[selected.status] ?? STATUS.nouvelle).cls}`}>
                    {(STATUS[selected.status] ?? STATUS.nouvelle).label}
                  </span>
                  {!readOnly && (
                    <button onClick={() => remove(selected)} className="p-1.5 text-red-400 hover:text-red-600" title="Supprimer">
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Indicateurs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Score</p>
                  <p className="text-lg font-bold text-gray-900">{selected.metrics.score}/100</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Taux d'effort</p>
                  <p className="text-lg font-bold text-gray-900">{pct(selected.metrics.effort_ratio)}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Dossier complet</p>
                  <p className="text-lg font-bold text-gray-900">{selected.metrics.completeness_pct} %</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-400">Garant</p>
                  <p className="text-lg font-bold text-gray-900">{selected.has_guarantor ? 'Oui' : 'Non'}</p>
                </div>
              </div>

              {/* Coordonnées & situation */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                {selected.email && <p><span className="text-gray-400">E-mail :</span> <span className="text-gray-800">{selected.email}</span></p>}
                {selected.phone && <p><span className="text-gray-400">Téléphone :</span> <span className="text-gray-800">{formatPhoneDisplay(selected.phone)}</span></p>}
                {selected.employment && <p><span className="text-gray-400">Situation :</span> <span className="text-gray-800">{selected.employment}</span></p>}
                {selected.monthly_income != null && <p><span className="text-gray-400">Revenus :</span> <span className="text-gray-800">{selected.monthly_income.toLocaleString('fr-FR')} € / mois</span></p>}
              </div>
              {selected.message && (
                <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">{selected.message}</p>
              )}

              {/* Checklist des pièces */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Pièces justificatives</h3>
                <ul className="space-y-1.5">
                  {selected.docs.map(d => (
                    <li key={d.key} className="flex items-center justify-between gap-3 text-sm bg-gray-50 rounded-lg px-3 py-2">
                      <span className="text-gray-700">{docLabels[d.key] ?? d.key}</span>
                      <span className="flex items-center gap-2 shrink-0">
                        <button onClick={() => toggleDoc(selected, d.key, 'provided')} disabled={busy || readOnly}
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${readOnly ? 'cursor-default' : ''} ${d.provided ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-500'}`}>
                          {d.provided ? 'Fournie' : 'À fournir'}
                        </button>
                        <button onClick={() => toggleDoc(selected, d.key, 'verified')} disabled={busy || !d.provided || readOnly}
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full disabled:opacity-40 ${readOnly ? 'cursor-default' : ''} ${d.verified ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-500'}`}>
                          {d.verified ? 'Vérifiée ✓' : 'À vérifier'}
                        </button>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Notes */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Notes internes</h3>
                <textarea defaultValue={selected.notes ?? ''} rows={2} readOnly={readOnly}
                  onBlur={e => { if (!readOnly && (selected.notes ?? '') !== e.target.value) patch(selected.id, { notes: e.target.value || null }) }}
                  placeholder={readOnly ? 'Aucune note' : 'Vos observations sur ce dossier…'}
                  className={`w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none ${readOnly ? 'bg-gray-50 text-gray-600' : ''}`} />
              </div>

              {/* Actions de statut */}
              <div className="flex flex-wrap gap-2 pt-1">
                {!readOnly && (<>
                  <button onClick={() => patch(selected.id, { status: 'en_etude' })} disabled={busy || selected.status === 'en_etude'}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-100 hover:bg-amber-200 text-amber-800 disabled:opacity-50">
                    <ShieldQuestion size={13} className="inline mr-1" />Mettre en étude
                  </button>
                  <button onClick={() => patch(selected.id, { status: 'retenue' })} disabled={busy || selected.status === 'retenue'}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-100 hover:bg-emerald-200 text-emerald-800 disabled:opacity-50">
                    <BadgeCheck size={13} className="inline mr-1" />Retenir ce candidat
                  </button>
                  <button onClick={() => patch(selected.id, { status: 'refusee' })} disabled={busy || selected.status === 'refusee'}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-600 disabled:opacity-50">
                    Refuser
                  </button>
                </>)}
                <button onClick={() => openCompare(selected.property_id)}
                  className="ml-auto px-3 py-1.5 rounded-lg text-xs font-semibold bg-violet-100 hover:bg-violet-200 text-violet-700">
                  <Scale size={13} className="inline mr-1" />Comparer
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Modale comparaison ── */}
      {showCompare && compare && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowCompare(false)}>
          <div className="bg-white rounded-xl w-full max-w-3xl p-6 max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2"><Scale size={17} /> Comparaison des profils</h3>
              <button onClick={() => setShowCompare(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              {compare.rent_reference != null
                ? `Loyer de référence : ${compare.rent_reference.toLocaleString('fr-FR')} € (annonce du bien).`
                : "Renseignez le loyer dans l'annonce du bien pour calculer le taux d'effort."}
              {' '}Classement par score (effort, complétude du dossier, garant).
            </p>
            {compare.candidates.length === 0 ? (
              <p className="text-sm text-gray-400">Aucune candidature active pour ce bien.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-400 uppercase tracking-wide text-left">
                    <th className="py-2 pr-3">Candidat</th>
                    <th className="py-2 pr-3">Revenus</th>
                    <th className="py-2 pr-3">Effort</th>
                    <th className="py-2 pr-3">Dossier</th>
                    <th className="py-2 pr-3">Garant</th>
                    <th className="py-2">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {compare.candidates.map((c, i) => (
                    <tr key={c.id} className={`border-t border-gray-100 ${i === 0 ? 'bg-emerald-50/60' : ''}`}>
                      <td className="py-2.5 pr-3">
                        <span className="font-medium text-gray-900">{c.full_name}</span>
                        {i === 0 && <span className="ml-2 text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">Recommandé</span>}
                        <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${(STATUS[c.status] ?? STATUS.nouvelle).cls}`}>{(STATUS[c.status] ?? STATUS.nouvelle).label}</span>
                      </td>
                      <td className="py-2.5 pr-3">{c.monthly_income != null ? `${c.monthly_income.toLocaleString('fr-FR')} €` : '—'}</td>
                      <td className="py-2.5 pr-3">{pct(c.metrics.effort_ratio)}</td>
                      <td className="py-2.5 pr-3">{c.metrics.completeness_pct} %</td>
                      <td className="py-2.5 pr-3">{c.has_guarantor ? 'Oui' : 'Non'}</td>
                      <td className="py-2.5 font-bold text-gray-900">{c.metrics.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ── Modale ajout manuel ── */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Nouveau dossier candidat</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <form onSubmit={createManual} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <select required value={form.property_id} onChange={e => setForm(f => ({ ...f, property_id: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm sm:col-span-2">
                <option value="">Bien concerné *</option>
                {props.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input required placeholder="Prénom *" value={form.first_name}
                onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input required placeholder="Nom *" value={form.last_name}
                onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input type="email" placeholder="E-mail" value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Téléphone" value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Situation professionnelle" value={form.employment}
                onChange={e => setForm(f => ({ ...f, employment: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input type="number" min="0" placeholder="Revenus mensuels (€)" value={form.monthly_income}
                onChange={e => setForm(f => ({ ...f, monthly_income: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <label className="flex items-center gap-2 text-sm text-gray-700 px-1">
                <input type="checkbox" checked={form.has_guarantor}
                  onChange={e => setForm(f => ({ ...f, has_guarantor: e.target.checked }))} />
                A un garant
              </label>
              <textarea placeholder="Message / contexte" value={form.message} rows={2}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none sm:col-span-2" />
              <div className="sm:col-span-2 flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Annuler</button>
                <button type="submit" disabled={busy}
                  className="px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-60" style={{ background: '#0D2F5C' }}>
                  {busy ? 'Enregistrement…' : 'Ajouter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
