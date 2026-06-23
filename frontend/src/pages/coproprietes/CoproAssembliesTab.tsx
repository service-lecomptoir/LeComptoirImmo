import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, FileDown, ArrowLeft, FileText } from 'lucide-react'
import { Button, Input } from '@/components/ui'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import { docFilename } from '@/utils/filename'
import {
  coproApi, type CoproDetail, type AssemblyListItem, type AssemblyDetail,
  type Voter, type Majority, type VoteChoice,
} from '@/api/coproprietes'

const MAJORITIES: { value: Majority; label: string }[] = [
  { value: 'art24', label: 'Majorité simple (art. 24)' },
  { value: 'art25', label: 'Majorité absolue (art. 25)' },
  { value: 'art26', label: 'Double majorité (art. 26)' },
  { value: 'unanimite', label: 'Unanimité' },
]
const MAJ_LABEL = Object.fromEntries(MAJORITIES.map(m => [m.value, m.label]))
const OUTCOME: Record<string, { label: string; cls: string }> = {
  adopted: { label: 'Adoptée', cls: 'text-green-700 bg-green-50' },
  rejected: { label: 'Rejetée', cls: 'text-red-700 bg-red-50' },
  pending: { label: 'Non soumise', cls: 'text-gray-500 bg-gray-100' },
}
const CHOICES: { value: VoteChoice; label: string; cls: string }[] = [
  { value: 'pour', label: 'Pour', cls: 'bg-green-600' },
  { value: 'contre', label: 'Contre', cls: 'bg-red-600' },
  { value: 'abstention', label: 'Abst.', cls: 'bg-gray-500' },
]

export function CoproAssembliesTab({ copro, canWrite }: { copro: CoproDetail; canWrite: boolean }) {
  const [list, setList] = useState<AssemblyListItem[]>([])
  const [voters, setVoters] = useState<Voter[]>([])
  const [selected, setSelected] = useState<AssemblyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  // création AG
  const [title, setTitle] = useState('')
  const [kind, setKind] = useState('ordinaire')
  const [mdate, setMdate] = useState('')
  const [location, setLocation] = useState('')
  const [creating, setCreating] = useState(false)
  // ajout résolution
  const [resTitle, setResTitle] = useState('')
  const [resMaj, setResMaj] = useState<Majority>('art24')
  const [pdfBusy, setPdfBusy] = useState(false)

  const loadList = useCallback(async () => {
    setLoading(true)
    try {
      const [l, v] = await Promise.all([coproApi.listAssemblies(copro.id), coproApi.voters(copro.id)])
      setList(l.data)
      setVoters(v.data)
    } catch (e) {
      toast.error(getErrorMessage(e, 'Erreur lors du chargement des assemblées'))
    } finally { setLoading(false) }
  }, [copro.id])

  useEffect(() => { loadList() }, [loadList])

  const open = async (id: string) => {
    try {
      const r = await coproApi.getAssembly(copro.id, id)
      setSelected(r.data)
    } catch (e) { toast.error(getErrorMessage(e, "Erreur lors de l'ouverture de l'assemblée")) }
  }

  const createAg = async () => {
    if (!title.trim()) { toast.error('Titre requis.'); return }
    setCreating(true)
    try {
      const r = await coproApi.createAssembly(copro.id, {
        title: title.trim(), kind, meeting_date: mdate || null, location: location.trim() || null,
      })
      toast.success('Assemblée créée')
      setTitle(''); setMdate(''); setLocation('')
      setSelected(r.data)
      loadList()
    } catch (e) {
      toast.error(getErrorMessage(e, "Erreur lors de la création"))
    } finally { setCreating(false) }
  }

  const removeAg = async (id: string) => {
    if (!window.confirm('Supprimer cette assemblée et ses résolutions ?')) return
    try {
      await coproApi.deleteAssembly(copro.id, id)
      toast.success('Assemblée supprimée')
      setSelected(null); loadList()
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  const addResolution = async () => {
    if (!selected) return
    if (!resTitle.trim()) { toast.error('Intitulé de la résolution requis.'); return }
    try {
      const r = await coproApi.addResolution(copro.id, selected.id, { title: resTitle.trim(), majority: resMaj })
      setResTitle('')
      setSelected(r.data)
    } catch (e) { toast.error(getErrorMessage(e, "Erreur lors de l'ajout de la résolution")) }
  }

  const delResolution = async (rid: string) => {
    if (!selected) return
    if (!window.confirm('Supprimer cette résolution ?')) return
    try {
      await coproApi.deleteResolution(copro.id, selected.id, rid)
      open(selected.id)
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors de la suppression')) }
  }

  const vote = async (rid: string, ownerId: string, choice: VoteChoice, current?: VoteChoice) => {
    if (!selected) return
    try {
      const r = current === choice
        ? await coproApi.clearVote(copro.id, selected.id, rid, ownerId)
        : await coproApi.setVote(copro.id, selected.id, rid, ownerId, choice)
      setSelected(r.data)
    } catch (e) { toast.error(getErrorMessage(e, "Erreur lors de l'enregistrement du vote")) }
  }

  const downloadPdf = async (which: 'conv' | 'pv') => {
    if (!selected) return
    setPdfBusy(true)
    try {
      const fn = docFilename(which === 'conv' ? 'convocation-ag' : 'pv-ag', { tenant: `${copro.name}_${selected.title}` })
      if (which === 'conv') await coproApi.convocationPdf(copro.id, selected.id, fn)
      else await coproApi.pvPdf(copro.id, selected.id, fn)
    } catch (e) { toast.error(getErrorMessage(e, 'Erreur lors du téléchargement')) }
    finally { setPdfBusy(false) }
  }

  if (loading) return <p className="text-sm text-gray-400 py-4">Chargement…</p>

  // ── Détail d'une assemblée ──
  if (selected) {
    const choiceOf = (rid: string, ownerId: string): VoteChoice | undefined =>
      selected.resolutions.find(r => r.id === rid)?.votes.find(v => v.owner_id === ownerId)?.choice
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <button onClick={() => { setSelected(null); loadList() }} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
            <ArrowLeft size={15} /> Toutes les assemblées
          </button>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => downloadPdf('conv')} disabled={pdfBusy} leftIcon={<FileText size={14} />}>Convocation</Button>
            <Button variant="secondary" size="sm" onClick={() => downloadPdf('pv')} disabled={pdfBusy} leftIcon={<FileDown size={14} />}>PV</Button>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="text-lg font-bold text-gray-900">{selected.title}</h3>
          <p className="text-sm text-gray-500">
            {selected.kind === 'extraordinaire' ? 'AG extraordinaire' : 'AG ordinaire'}
            {selected.meeting_date ? ` · ${new Date(selected.meeting_date).toLocaleDateString('fr-FR')}` : ''}
            {selected.location ? ` · ${selected.location}` : ''}
          </p>
        </div>

        {/* Résolutions */}
        {selected.resolutions.map((r, i) => (
          <div key={r.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="flex items-center justify-between bg-gray-50 px-4 py-2 border-b border-gray-200">
              <div>
                <span className="text-sm font-semibold text-gray-900">Résolution {i + 1} : {r.title}</span>
                <span className="ml-2 text-xs text-gray-500">{MAJ_LABEL[r.majority]}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs rounded-full px-2 py-0.5 ${OUTCOME[r.outcome]?.cls}`}>{OUTCOME[r.outcome]?.label}</span>
                {canWrite && <button onClick={() => delResolution(r.id)} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button>}
              </div>
            </div>
            <div className="px-4 py-2 text-xs text-gray-600 flex flex-wrap gap-x-5">
              <span>Pour : <strong className="text-green-700">{r.pour} t</strong></span>
              <span>Contre : <strong className="text-red-700">{r.contre} t</strong></span>
              <span>Abstention : <strong>{r.abstention} t</strong></span>
              <span className="text-gray-400">Base : {r.base_tantiemes} tantièmes</span>
            </div>
            {/* Grille de vote */}
            <table className="w-full text-sm">
              <tbody>
                {voters.map(v => {
                  const cur = choiceOf(r.id, v.owner_id)
                  return (
                    <tr key={v.owner_id} className="border-t border-gray-100">
                      <td className="px-4 py-1.5">{v.owner_name}</td>
                      <td className="px-4 py-1.5 text-gray-400 text-right whitespace-nowrap">{v.tantiemes} t</td>
                      <td className="px-4 py-1.5 text-right">
                        {canWrite ? (
                          <div className="inline-flex gap-1">
                            {CHOICES.map(c => (
                              <button key={c.value} onClick={() => vote(r.id, v.owner_id, c.value, cur)}
                                className={`px-2 py-0.5 rounded text-xs text-white ${cur === c.value ? c.cls : 'bg-gray-200 text-gray-600'}`}>
                                {c.label}
                              </button>
                            ))}
                          </div>
                        ) : (cur ? CHOICES.find(c => c.value === cur)?.label : '—')}
                      </td>
                    </tr>
                  )
                })}
                {voters.length === 0 && <tr><td colSpan={3} className="px-4 py-2 text-gray-400">Aucun copropriétaire avec des tantièmes généraux.</td></tr>}
              </tbody>
            </table>
          </div>
        ))}
        {selected.resolutions.length === 0 && <p className="text-sm text-gray-400">Aucune résolution à l'ordre du jour.</p>}

        {canWrite && (
          <div className="bg-white rounded-xl border border-gray-200 p-3 flex flex-wrap items-end gap-2">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-[11px] text-gray-600 mb-1">Nouvelle résolution</label>
              <Input value={resTitle} onChange={e => setResTitle(e.target.value)} placeholder="Approbation des comptes" />
            </div>
            <div>
              <label className="block text-[11px] text-gray-600 mb-1">Majorité</label>
              <select value={resMaj} onChange={e => setResMaj(e.target.value as Majority)} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
                {MAJORITIES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <Button size="sm" onClick={addResolution} leftIcon={<Plus size={14} />}>Ajouter</Button>
          </div>
        )}
      </div>
    )
  }

  // ── Liste des assemblées ──
  return (
    <div className="space-y-4">
      {canWrite && (
        <div className="bg-white rounded-xl border border-gray-200 p-3 flex flex-wrap items-end gap-2">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-[11px] text-gray-600 mb-1">Titre de l'assemblée</label>
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Assemblée générale 2026" />
          </div>
          <div>
            <label className="block text-[11px] text-gray-600 mb-1">Type</label>
            <select value={kind} onChange={e => setKind(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="ordinaire">Ordinaire</option>
              <option value="extraordinaire">Extraordinaire</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] text-gray-600 mb-1">Date</label>
            <input type="date" value={mdate} onChange={e => setMdate(e.target.value)} className="px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div className="flex-1 min-w-[160px]">
            <label className="block text-[11px] text-gray-600 mb-1">Lieu</label>
            <Input value={location} onChange={e => setLocation(e.target.value)} placeholder="(optionnel)" />
          </div>
          <Button size="sm" onClick={createAg} isLoading={creating} leftIcon={<Plus size={14} />}>Créer</Button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {list.length === 0 ? (
          <p className="px-4 py-6 text-sm text-gray-400">Aucune assemblée.</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500 uppercase">
              <th className="px-4 py-2">Assemblée</th><th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">Date</th><th className="px-4 py-2 text-center">Résolutions</th>{canWrite && <th className="px-4 py-2" />}
            </tr></thead>
            <tbody>
              {list.map(a => (
                <tr key={a.id} className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => open(a.id)}>
                  <td className="px-4 py-2 font-medium text-gray-900">{a.title}</td>
                  <td className="px-4 py-2 text-gray-600">{a.kind === 'extraordinaire' ? 'Extraordinaire' : 'Ordinaire'}</td>
                  <td className="px-4 py-2 text-gray-600">{a.meeting_date ? new Date(a.meeting_date).toLocaleDateString('fr-FR') : '-'}</td>
                  <td className="px-4 py-2 text-center">{a.resolution_count}</td>
                  {canWrite && (
                    <td className="px-4 py-2 text-right" onClick={e => e.stopPropagation()}>
                      <button onClick={() => removeAg(a.id)} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600" title="Supprimer"><Trash2 size={14} /></button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
