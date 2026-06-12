import { useState, useEffect } from 'react'
import { MessageSquare, Plus, Clock, CheckCircle, AlertCircle, XCircle, Send, Check, X, RotateCcw, Pencil, Sparkles, DoorOpen } from 'lucide-react'
import { ticketsApi, type Ticket } from '@/api/tickets'
import { leaseExitsApi } from '@/api/leaseExits'
import { toast } from '@/store/toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  open:            { label: 'Ouvert',            color: '#D97706', bg: '#FEF3C7', icon: Clock },
  in_progress:     { label: 'En cours',          color: '#2563EB', bg: '#DBEAFE', icon: AlertCircle },
  resolved:        { label: 'Résolu',            color: '#059669', bg: '#D1FAE5', icon: CheckCircle },
  pending_closure: { label: 'Clôture à valider', color: '#7C3AED', bg: '#EDE9FE', icon: AlertCircle },
  closed:          { label: 'Clôturé',           color: '#6B7280', bg: '#F3F4F6', icon: XCircle },
}

const CATEGORY_LABELS: Record<string, string> = {
  incident: 'Incident',
  question: 'Question',
  demande:  'Demande',
  autre:    'Autre',
}

// Types de signalement proposés au locataire. Chaque type est routé vers l'agent
// IA compétent côté gestionnaire (voisinage → Sécurité, logement → Administratif).
// Le paiement se déclare via l'espace « loyers », pas ici.
const TOPIC_OPTIONS: { value: string; label: string; category: string }[] = [
  { value: 'logement',  label: 'Problème dans le logement (fuite, panne…)', category: 'incident' },
  { value: 'voisinage', label: 'Problème de voisinage',                      category: 'incident' },
  { value: 'autre',     label: 'Autre demande',                              category: 'autre' },
]
const TOPIC_LABELS: Record<string, string> = {
  voisinage: 'Voisinage', logement: 'Logement', paiement: 'Paiement', autre: 'Autre',
}
const topicOrCategory = (t: Ticket) =>
  (t.topic && TOPIC_LABELS[t.topic]) || CATEGORY_LABELS[t.category] || 'Autre'

const PRIORITY_LABELS: Record<string, { label: string; color: string }> = {
  low:    { label: 'Basse',   color: '#6B7280' },
  medium: { label: 'Normale', color: '#2563EB' },
  high:   { label: 'Haute',   color: '#D97706' },
  urgent: { label: 'Urgent',  color: '#DC2626' },
}

export default function LocataireMessages() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selected, setSelected] = useState<Ticket | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [reply, setReply] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isActing, setIsActing] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  // Nouveau ticket — `topic` pilote l'agent notifié ; la catégorie en est dérivée.
  const [form, setForm] = useState({ title: '', description: '', topic: 'logement', priority: 'medium' })
  const [isCreating, setIsCreating] = useState(false)
  const [generating, setGenerating] = useState(false)

  // Préavis de départ
  const [preavis, setPreavis] = useState<{ sent: boolean; status: string | null; departure_date: string | null; notice_received_at: string | null } | null>(null)
  const [showPreavis, setShowPreavis] = useState(false)
  const [preavisDate, setPreavisDate] = useState('')
  const [sendingPreavis, setSendingPreavis] = useState(false)

  const loadPreavis = () => {
    leaseExitsApi.myPreavis().then(r => setPreavis(r.data)).catch(() => {})
  }
  useEffect(() => { loadPreavis() }, [])

  const generateDraft = async () => {
    setGenerating(true)
    try {
      const { data } = await ticketsApi.draft({ topic: form.topic, hint: form.description })
      setForm(f => ({ ...f, title: data.title, description: data.description }))
      toast.success(data.source === 'ia' ? "Brouillon rédigé par l'IA." : 'Brouillon proposé.')
    } catch { /* intercepteur affiche l'erreur */ } finally { setGenerating(false) }
  }

  const sendPreavis = async () => {
    setSendingPreavis(true)
    try {
      await leaseExitsApi.sendPreavis(preavisDate || null)
      setShowPreavis(false); setPreavisDate('')
      loadPreavis()
      toast.success('Préavis de départ envoyé à votre gestionnaire.')
    } catch { /* intercepteur affiche l'erreur */ } finally { setSendingPreavis(false) }
  }

  const load = async () => {
    setIsLoading(true)
    try {
      const res = await ticketsApi.mine()
      setTickets(res.data)
    } catch { /* */ }
    finally { setIsLoading(false) }
  }

  useEffect(() => { load() }, [])

  const loadDetail = async (id: string) => {
    try {
      const res = await ticketsApi.get(id)
      setSelected(res.data)
    } catch { /* */ }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title || !form.description) return
    setIsCreating(true)
    try {
      const category = TOPIC_OPTIONS.find(o => o.value === form.topic)?.category ?? 'autre'
      await ticketsApi.create({
        title: form.title, description: form.description,
        category, priority: form.priority, topic: form.topic,
      })
      setShowForm(false)
      setForm({ title: '', description: '', topic: 'logement', priority: 'medium' })
      await load()
    } finally { setIsCreating(false) }
  }

  const handleReply = async () => {
    if (!reply.trim() || !selected) return
    setIsSending(true)
    try {
      await ticketsApi.addMessage(selected.id, reply)
      setReply('')
      await loadDetail(selected.id)
    } finally { setIsSending(false) }
  }

  const refreshAll = async (id: string) => {
    await loadDetail(id)
    await load()
  }

  const handleValidate = async () => {
    if (!selected) return
    setIsActing(true)
    try {
      await ticketsApi.validateClosure(selected.id)
      await refreshAll(selected.id)
    } finally { setIsActing(false) }
  }

  const handleRefuse = async () => {
    if (!selected) return
    const motif = window.prompt('Pourquoi refusez-vous la clôture de cette démarche ? (facultatif)') ?? ''
    setIsActing(true)
    try {
      await ticketsApi.refuseClosure(selected.id, motif.trim() || undefined)
      await refreshAll(selected.id)
    } finally { setIsActing(false) }
  }

  const handleRelancer = async () => {
    if (!selected) return
    const motif = window.prompt('Ajoutez un message à votre relance (facultatif) :') ?? ''
    setIsActing(true)
    try {
      await ticketsApi.relancer(selected.id, motif.trim() || undefined)
      await refreshAll(selected.id)
    } finally { setIsActing(false) }
  }

  const startEdit = (id: string, content: string) => {
    setEditingId(id)
    setEditContent(content)
  }

  const handleSaveEdit = async () => {
    if (!selected || !editingId || !editContent.trim()) return
    setIsActing(true)
    try {
      await ticketsApi.editMessage(selected.id, editingId, editContent.trim())
      setEditingId(null)
      setEditContent('')
      await loadDetail(selected.id)
    } finally { setIsActing(false) }
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mes démarches</h1>
          <p className="text-gray-500 text-sm mt-1">Faites une demande à votre gestionnaire et suivez son évolution</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setShowPreavis(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            <DoorOpen size={16} />
            Envoyer un préavis de départ
          </button>
          <button
            onClick={() => { setShowForm(true); setSelected(null) }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white"
            style={{ background: '#0D2F5C' }}
          >
            <Plus size={16} />
            Nouvelle démarche
          </button>
        </div>
      </div>

      {/* Bandeau préavis envoyé */}
      {preavis?.sent && preavis.status !== 'cloture' && (
        <div className="mb-5 flex items-center gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
          <DoorOpen size={15} className="shrink-0" />
          <span>
            Préavis de départ transmis
            {preavis.notice_received_at ? ` le ${format(new Date(preavis.notice_received_at), 'd MMM yyyy', { locale: fr })}` : ''}
            {preavis.departure_date ? ` : départ prévu le ${format(new Date(preavis.departure_date), 'd MMM yyyy', { locale: fr })}` : ''}.
            Votre gestionnaire organisera l'état des lieux de sortie.
          </span>
        </div>
      )}

      {/* Formulaire nouveau ticket */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-4">Nouvelle démarche</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type de signalement</label>
                <select
                  value={form.topic}
                  onChange={e => setForm(f => ({ ...f, topic: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  {TOPIC_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Priorité</label>
                <select
                  value={form.priority}
                  onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="low">Basse</option>
                  <option value="medium">Normale</option>
                  <option value="high">Haute</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
            </div>
            <div className="flex items-center justify-between gap-3 flex-wrap rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
              <p className="text-xs text-gray-500">Besoin d'aide ? L'IA peut rédiger le sujet et le message d'après le type choisi (et vos quelques mots ci-dessous).</p>
              <button type="button" onClick={generateDraft} disabled={generating}
                className="inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-lg text-white disabled:opacity-60"
                style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #0E9F8E 130%)' }}>
                <Sparkles size={14} /> {generating ? 'Rédaction…' : "Rédiger avec l'IA"}
              </button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sujet</label>
              <input
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Résumez votre demande en quelques mots…"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Décrivez votre problème ou demande en détail…"
                rows={4}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none"
                required
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">
                Annuler
              </button>
              <button type="submit" disabled={isCreating}
                className="px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-60"
                style={{ background: '#0D2F5C' }}>
                {isCreating ? 'Envoi…' : 'Envoyer'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Liste des tickets */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {isLoading ? (
              <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
            ) : tickets.length === 0 ? (
              <div className="py-12 text-center">
                <MessageSquare size={32} className="mx-auto mb-2 text-gray-300" />
                <p className="text-sm text-gray-400">Aucune démarche</p>
                <p className="text-xs text-gray-400 mt-1">Cliquez sur "Nouvelle démarche" pour en créer une</p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {tickets.map(ticket => {
                  const sc = STATUS_CONFIG[ticket.status] ?? STATUS_CONFIG.open
                  const Icon = sc.icon
                  return (
                    <li key={ticket.id}>
                      <button
                        onClick={() => loadDetail(ticket.id)}
                        className={`w-full text-left px-4 py-3.5 hover:bg-gray-50 transition-colors ${selected?.id === ticket.id ? 'bg-blue-50' : ''}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-gray-900 truncate flex-1">{ticket.title}</p>
                          <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0"
                            style={{ color: sc.color, background: sc.bg }}>
                            <Icon size={10} />
                            {sc.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-400">{topicOrCategory(ticket)}</span>
                          <span className="text-gray-300">·</span>
                          <span className="text-xs text-gray-400">
                            {format(new Date(ticket.created_at), 'd MMM yyyy', { locale: fr })}
                          </span>
                        </div>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>

        {/* Détail / Conversation */}
        <div className="lg:col-span-2">
          {!selected ? (
            <div className="bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center h-64">
              <MessageSquare size={36} className="text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Sélectionnez une démarche pour suivre son évolution</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 flex flex-col" style={{ minHeight: '400px' }}>
              {/* Header */}
              <div className="px-5 py-4 border-b border-gray-100">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-gray-900">{selected.title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">{topicOrCategory(selected)}</span>
                      <span className="text-gray-300">·</span>
                      <span className="text-xs font-medium" style={{ color: PRIORITY_LABELS[selected.priority]?.color }}>
                        {PRIORITY_LABELS[selected.priority]?.label}
                      </span>
                    </div>
                  </div>
                  {(() => {
                    const sc = STATUS_CONFIG[selected.status] ?? STATUS_CONFIG.open
                    const Icon = sc.icon
                    return (
                      <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full"
                        style={{ color: sc.color, background: sc.bg }}>
                        <Icon size={11} />
                        {sc.label}
                      </span>
                    )
                  })()}
                </div>
              </div>

              {/* Barre d'actions de la démarche */}
              {selected.status !== 'closed' && (
                <div className="px-5 py-3 border-b border-gray-100 bg-gray-50 flex flex-wrap items-center gap-2">
                  {selected.status === 'pending_closure' ? (
                    <>
                      <span className="text-xs text-gray-600 mr-1">
                        Votre gestionnaire propose de clôturer cette démarche :
                      </span>
                      <button
                        onClick={handleValidate}
                        disabled={isActing}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white disabled:opacity-50"
                        style={{ background: '#059669' }}
                      >
                        <Check size={13} />
                        Valider la clôture
                      </button>
                      <button
                        onClick={handleRefuse}
                        disabled={isActing}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold disabled:opacity-50"
                        style={{ color: '#DC2626', background: '#FEE2E2' }}
                      >
                        <X size={13} />
                        Refuser la clôture
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={handleRelancer}
                      disabled={isActing}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold disabled:opacity-50"
                      style={{ color: '#0D2F5C', background: '#E0E7FF' }}
                    >
                      <RotateCcw size={13} />
                      Relancer
                    </button>
                  )}
                </div>
              )}

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
                {(selected.messages ?? []).map(msg => {
                  const isMe = msg.author_role === 'locataire'
                  const isEditing = editingId === msg.id
                  return (
                    <div key={msg.id} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-xl px-4 py-3 ${isMe ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
                        {!isMe && (
                          <p className="text-xs font-semibold mb-1 text-gray-500">{msg.author_name ?? 'Gestionnaire'}</p>
                        )}
                        {isEditing ? (
                          <div className="space-y-2">
                            <textarea
                              value={editContent}
                              onChange={e => setEditContent(e.target.value)}
                              rows={3}
                              className="w-full rounded-lg px-2 py-1.5 text-sm text-gray-900 border border-white/40 resize-none"
                            />
                            <div className="flex gap-2 justify-end">
                              <button onClick={() => setEditingId(null)}
                                className="px-2.5 py-1 text-xs rounded-md bg-white/20 hover:bg-white/30">
                                Annuler
                              </button>
                              <button onClick={handleSaveEdit} disabled={isActing || !editContent.trim()}
                                className="px-2.5 py-1 text-xs rounded-md bg-white text-blue-700 font-semibold disabled:opacity-50">
                                Enregistrer
                              </button>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        )}
                        <div className={`flex items-center gap-2 mt-1.5 ${isMe ? 'text-blue-200' : 'text-gray-400'}`}>
                          <span className="text-xs">{format(new Date(msg.created_at), 'dd/MM/yyyy HH:mm')}</span>
                          {isMe && !isEditing && selected.status !== 'closed' && (
                            <button
                              onClick={() => startEdit(msg.id, msg.content)}
                              className="flex items-center gap-1 text-xs hover:text-white transition-colors"
                              title="Modifier mon commentaire"
                            >
                              <Pencil size={11} />
                              Modifier
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Réponse (seulement si ticket pas clôturé) */}
              {selected.status !== 'closed' && (
                <div className="px-5 py-4 border-t border-gray-100">
                  <div className="flex gap-3">
                    <textarea
                      value={reply}
                      onChange={e => setReply(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleReply() } }}
                      placeholder="Votre réponse… (Entrée pour envoyer)"
                      rows={2}
                      className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm resize-none focus:outline-none focus:border-blue-400"
                    />
                    <button
                      onClick={handleReply}
                      disabled={isSending || !reply.trim()}
                      className="px-4 rounded-xl text-white disabled:opacity-40 flex items-center"
                      style={{ background: '#0D2F5C' }}
                    >
                      <Send size={16} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Modale : préavis de départ ── */}
      {showPreavis && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2"><DoorOpen size={17} /> Préavis de départ</h3>
              <button onClick={() => setShowPreavis(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Informez votre gestionnaire de votre intention de quitter le logement. Il organisera l'état
              des lieux de sortie et le décompte du dépôt de garantie.
            </p>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date de départ souhaitée (facultatif)</label>
            <input type="date" value={preavisDate} onChange={e => setPreavisDate(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
            <p className="text-xs text-gray-400 mt-1">Vous pourrez en convenir précisément avec votre gestionnaire.</p>
            <div className="flex justify-end gap-3 mt-5">
              <button type="button" onClick={() => setShowPreavis(false)}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Annuler</button>
              <button type="button" onClick={sendPreavis} disabled={sendingPreavis}
                className="px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-60" style={{ background: '#0D2F5C' }}>
                {sendingPreavis ? 'Envoi…' : 'Envoyer le préavis'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
