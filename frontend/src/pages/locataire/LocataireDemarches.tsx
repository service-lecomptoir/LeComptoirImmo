import { useState, useEffect, useCallback } from 'react'
import { X, Plus, Send, Sparkles, MessageSquare, ChevronDown, CheckCircle, Camera } from 'lucide-react'
import { ticketsApi, type Ticket } from '@/api/tickets'
import { leaseExitsApi } from '@/api/leaseExits'
import { StatusBadge } from '@/components/common/StatusBadge'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// La valeur « preavis » n'est pas une catégorie de ticket : elle déclenche
// l'envoi d'un préavis de départ (flux dédié) au lieu de créer une démarche.
const CATEGORIES: { v: string; label: string }[] = [
  { v: 'demande', label: 'Demande' },
  { v: 'question', label: 'Question' },
  { v: 'incident', label: 'Incident' },
  { v: 'preavis', label: 'Préavis de départ' },
  { v: 'autre', label: 'Autre' },
]
const PRIORITIES: { v: Ticket['priority']; label: string }[] = [
  { v: 'low', label: 'Basse' },
  { v: 'medium', label: 'Moyenne' },
  { v: 'high', label: 'Haute' },
  { v: 'urgent', label: 'Urgente' },
]
const CAT_LABEL: Record<string, string> = { demande: 'Demande', question: 'Question', incident: 'Incident', autre: 'Autre' }
const STATUT: Record<string, { label: string; variant: 'green' | 'blue' | 'yellow' | 'red' | 'gray' }> = {
  open: { label: 'Ouverte', variant: 'blue' },
  in_progress: { label: 'En cours', variant: 'yellow' },
  resolved: { label: 'Résolue', variant: 'green' },
  pending_closure: { label: 'Clôture proposée', variant: 'yellow' },
  closed: { label: 'Clôturée', variant: 'gray' },
}

export default function LocataireDemarches() {
  // Date de départ saisie quand le type « Préavis de départ » est choisi dans
  // la modale « Nouvelle démarche » (le préavis n'a plus de carte dédiée en haut).
  const [preavisDate, setPreavisDate] = useState('')

  // ── Démarches (tickets) ─────────────────────────────────────────────────────
  const [items, setItems] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [openId, setOpenId] = useState<string | null>(null)
  const [detail, setDetail] = useState<Ticket | null>(null)
  const [reply, setReply] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [form, setForm] = useState<{ title: string; category: string; priority: Ticket['priority']; description: string }>(
    { title: '', category: 'demande', priority: 'medium', description: '' })
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [drafting, setDrafting] = useState(false)
  const resetNew = () => { setForm({ title: '', category: 'demande', priority: 'medium', description: '' }); setPhotoFile(null); setPreavisDate('') }

  const load = useCallback(async () => {
    setLoading(true)
    try { const { data } = await ticketsApi.mine(); setItems(data) }
    catch { /* intercepteur */ } finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const toggle = async (id: string) => {
    if (openId === id) { setOpenId(null); setDetail(null); return }
    setOpenId(id); setDetail(null); setReply('')
    try { const { data } = await ticketsApi.get(id); setDetail(data) } catch { /* */ }
  }

  const submitNew = async () => {
    // Cas « Préavis de départ » : flux dédié (pas une démarche/ticket).
    if (form.category === 'preavis') {
      setSubmitting(true)
      try {
        await leaseExitsApi.sendPreavis(preavisDate || null)
        setShowNew(false); resetNew()
        toast.success('Préavis de départ envoyé à votre gestionnaire.')
      } catch (e) { toast.error(getErrorMessage(e, "Le préavis n'a pas pu être envoyé")) }
      finally { setSubmitting(false) }
      return
    }
    if (!form.title.trim() || !form.description.trim()) { toast.error('Objet et description requis.'); return }
    setSubmitting(true)
    try {
      const { data } = await ticketsApi.create({
        title: form.title.trim(), description: form.description.trim(),
        category: form.category, priority: form.priority,
      })
      if (photoFile && data?.id) {
        try { await ticketsApi.uploadPhoto(data.id, photoFile) }
        catch (e) { toast.error(getErrorMessage(e, "La photo n'a pas pu être envoyée")) }
      }
      setShowNew(false); resetNew()
      toast.success('Démarche envoyée à votre gestionnaire.')
      await load()
    } catch (e) { toast.error(getErrorMessage(e, "La démarche n'a pas pu être envoyée")) }
    finally { setSubmitting(false) }
  }

  const aiDraft = async () => {
    setDrafting(true)
    try {
      const { data } = await ticketsApi.draft({ hint: form.description || form.title || undefined })
      setForm(f => ({ ...f, title: data.title || f.title, description: data.description || f.description }))
    } catch (e) { toast.error(getErrorMessage(e, "La rédaction assistée a échoué")) }
    finally { setDrafting(false) }
  }

  const sendReply = async (id: string) => {
    if (!reply.trim()) return
    try {
      await ticketsApi.addMessage(id, reply.trim())
      setReply('')
      const { data } = await ticketsApi.get(id); setDetail(data)
    } catch (e) { toast.error(getErrorMessage(e, "Le message n'a pas pu être envoyé")) }
  }

  const validateClosure = async (id: string) => {
    try { await ticketsApi.validateClosure(id); toast.success('Démarche clôturée.'); await load(); setOpenId(null) }
    catch (e) { toast.error(getErrorMessage(e, "Échec de la clôture")) }
  }
  const refuseClosure = async (id: string) => {
    try { await ticketsApi.refuseClosure(id); toast.success('Clôture refusée, la démarche reste ouverte.'); const { data } = await ticketsApi.get(id); setDetail(data); await load() }
    catch (e) { toast.error(getErrorMessage(e, "Échec")) }
  }

  return (
    <div className="max-w-3xl p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageSquare size={22} className="text-[#0D2F5C]" /> Mes démarches
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Vos échanges avec votre gestionnaire au sujet de votre logement : demandes, questions, incidents,
          et envoi de votre préavis de départ.
        </p>
      </div>

      {/* Démarches */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-900">Mes échanges</h2>
        <button onClick={() => setShowNew(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-white rounded-lg"
          style={{ background: '#0D2F5C' }}>
          <Plus size={15} /> Nouvelle démarche
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">Chargement…</p>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          <MessageSquare size={30} className="mx-auto mb-2 text-gray-300" />
          <p className="text-sm">Aucune démarche pour le moment.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(t => {
            const st = STATUT[t.status] ?? { label: t.status, variant: 'gray' as const }
            const isOpen = openId === t.id
            return (
              <div key={t.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button onClick={() => toggle(t.id)} className="w-full flex items-start justify-between gap-3 p-4 text-left hover:bg-gray-50">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900">{t.title}</span>
                      <span className="text-xs text-gray-400">{CAT_LABEL[t.category] ?? t.category}</span>
                      <StatusBadge label={st.label} variant={st.variant} dot />
                    </div>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{t.description}</p>
                    <p className="text-xs text-gray-400 mt-1">Créée le {format(new Date(t.created_at), 'd MMM yyyy', { locale: fr })}</p>
                  </div>
                  <ChevronDown size={18} className={`text-gray-400 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </button>

                {isOpen && (
                  <div className="border-t border-gray-100 p-4 space-y-3">
                    {detail?.status === 'pending_closure' && (
                      <div className="flex items-center justify-between gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-sm text-amber-800">
                        <span>Votre gestionnaire propose de clôturer cette démarche.</span>
                        <div className="flex gap-2 shrink-0">
                          <button onClick={() => validateClosure(t.id)} className="px-3 py-1 rounded-lg bg-green-600 text-white text-xs font-medium">Valider</button>
                          <button onClick={() => refuseClosure(t.id)} className="px-3 py-1 rounded-lg border border-gray-300 text-gray-700 text-xs">Refuser</button>
                        </div>
                      </div>
                    )}
                    {detail?.photo_url && (
                      <a href={`${API_BASE}${detail.photo_url}`} target="_blank" rel="noreferrer" className="inline-block">
                        <img src={`${API_BASE}${detail.photo_url}`} alt="photo de la démarche" className="max-h-40 rounded-lg border border-gray-200" />
                      </a>
                    )}
                    <div className="space-y-2">
                      {(detail?.messages ?? []).filter(m => !m.is_internal).map(m => {
                        const mine = m.author_role === 'locataire'
                        return (
                          <div key={m.id} className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${mine ? 'ml-auto bg-blue-50 text-blue-900' : 'bg-gray-100 text-gray-800'}`}>
                            <p className="text-[11px] font-medium opacity-70 mb-0.5">{mine ? 'Vous' : (m.author_name || 'Gestionnaire')}</p>
                            <p className="whitespace-pre-line">{m.content}</p>
                          </div>
                        )
                      })}
                      {detail && (detail.messages ?? []).filter(m => !m.is_internal).length === 0 && (
                        <p className="text-xs text-gray-400">Pas encore de réponse.</p>
                      )}
                    </div>
                    {t.status !== 'closed' && (
                      <div className="flex items-center gap-2">
                        <input value={reply} onChange={e => setReply(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') sendReply(t.id) }}
                          placeholder="Votre message…"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        <button onClick={() => sendReply(t.id)} disabled={!reply.trim()}
                          className="p-2 rounded-lg text-white disabled:opacity-40" style={{ background: '#0D2F5C' }}><Send size={15} /></button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── Modale : nouvelle démarche ── */}
      {showNew && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Nouvelle démarche</h3>
              <button onClick={() => setShowNew(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  {CATEGORIES.map(c => <option key={c.v} value={c.v}>{c.label}</option>)}
                </select>
              </div>

              {form.category === 'preavis' ? (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <p className="text-sm text-amber-800 mb-2">
                    Vous informez votre gestionnaire de votre intention de quitter le logement. Il organisera l'état des lieux de sortie et le décompte du dépôt de garantie.
                  </p>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Date de départ souhaitée (facultatif)</label>
                  <input type="date" value={preavisDate} onChange={e => setPreavisDate(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white" />
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Objet</label>
                    <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                      placeholder="Ex. Fuite sous l'évier de la cuisine"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Priorité</label>
                    <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value as Ticket['priority'] })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                      {PRIORITIES.map(p => <option key={p.v} value={p.v}>{p.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-medium text-gray-700">Description</label>
                      <button type="button" onClick={aiDraft} disabled={drafting}
                        className="inline-flex items-center gap-1 text-xs text-[#0D2F5C] hover:underline disabled:opacity-50">
                        <Sparkles size={12} /> {drafting ? 'Rédaction…' : 'Aide à la rédaction'}
                      </button>
                    </div>
                    <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={4}
                      placeholder="Décrivez votre demande à votre gestionnaire."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Photo (facultatif)</label>
                    {photoFile ? (
                      <div className="flex items-center gap-2 text-sm text-gray-700">
                        <Camera size={15} className="text-gray-400" /> {photoFile.name}
                        <button type="button" onClick={() => setPhotoFile(null)} className="text-gray-400 hover:text-red-600"><X size={15} /></button>
                      </div>
                    ) : (
                      <label className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 cursor-pointer">
                        <Camera size={15} /> Ajouter une photo
                        <input type="file" accept="image/*" className="hidden"
                          onChange={e => setPhotoFile(e.target.files?.[0] || null)} />
                      </label>
                    )}
                  </div>
                </>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button type="button" onClick={() => { setShowNew(false); resetNew() }}
                className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">Annuler</button>
              <button type="button" onClick={submitNew} disabled={submitting}
                className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-60" style={{ background: '#0D2F5C' }}>
                <CheckCircle size={15} /> {submitting ? 'Envoi…' : (form.category === 'preavis' ? 'Envoyer le préavis' : 'Envoyer la démarche')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
