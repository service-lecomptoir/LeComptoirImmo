import { useState, useEffect, useRef } from 'react'
import { MessageSquare, Clock, AlertCircle, CheckCircle, XCircle, Send, User, Building2 } from 'lucide-react'
import { ticketsApi, type Ticket } from '@/api/tickets'
import { messagesApi, type ProprietaireMessage, type Conversation } from '@/api/messages'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { useAuthStore } from '@/store/authStore'

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  open:        { label: 'Ouvert',    color: '#D97706', bg: '#FEF3C7', icon: Clock },
  in_progress: { label: 'En cours',  color: '#2563EB', bg: '#DBEAFE', icon: AlertCircle },
  resolved:    { label: 'Résolu',    color: '#059669', bg: '#D1FAE5', icon: CheckCircle },
  closed:      { label: 'Clôturé',   color: '#6B7280', bg: '#F3F4F6', icon: XCircle },
}

const CATEGORY_LABELS: Record<string, string> = {
  incident: '🔴 Incident',
  question: '💬 Question',
  demande:  '📋 Demande',
  autre:    '📌 Autre',
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string }> = {
  low:    { label: 'Basse',   color: '#6B7280' },
  medium: { label: 'Normale', color: '#2563EB' },
  high:   { label: 'Haute',   color: '#D97706' },
  urgent: { label: 'Urgent',  color: '#DC2626' },
}

const FILTERS = [
  { value: '', label: 'Tous' },
  { value: 'open', label: 'Ouverts' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'resolved', label: 'Résolus' },
  { value: 'closed', label: 'Clôturés' },
]

type FetchFn = (params?: { status?: string }) => Promise<{ data: { total: number; items: Ticket[] } }>

// ── Composant onglet tickets ────────────────────────────────────────────────────

function TicketsTab({
  readOnly = false,
  fetchFn,
}: {
  readOnly?: boolean
  fetchFn?: FetchFn
}) {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<Ticket | null>(null)
  const [reply, setReply] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [newStatus, setNewStatus] = useState<string>('')
  const [statusError, setStatusError] = useState('')

  const listFn: FetchFn = fetchFn ?? ((params) => ticketsApi.list({ ...params, limit: 100 }))

  const load = async (currentFilter: string) => {
    setIsLoading(true)
    try {
      const res = await listFn({ status: currentFilter || undefined })
      setTickets(res.data.items)
      setTotal(res.data.total)
    } catch { /* */ }
    finally { setIsLoading(false) }
  }

  const loadDetail = async (id: string) => {
    try {
      const res = await ticketsApi.get(id)
      setSelected(res.data)
      setNewStatus(res.data.status)
    } catch { /* */ }
  }

  useEffect(() => { load(filter) }, [filter])

  const handleReply = async () => {
    if (!reply.trim() || !selected) return
    setIsSending(true)
    try {
      await ticketsApi.addMessage(selected.id, reply)
      setReply('')
      await loadDetail(selected.id)
    } finally { setIsSending(false) }
  }

  const handleStatusChange = async (status: string) => {
    if (!selected) return
    setStatusError('')
    try {
      await ticketsApi.update(selected.id, { status: status as any })
      setNewStatus(status)
      await loadDetail(selected.id)
      await load(filter)
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? 'Erreur lors de la mise à jour du statut'
      setStatusError(msg)
      setTimeout(() => setStatusError(''), 4000)
    }
  }

  const openCount = tickets.filter(t => t.status === 'open').length

  return (
    <div>
      {/* Counter */}
      {openCount > 0 && (
        <span className="inline-flex mb-4 px-2.5 py-0.5 bg-red-100 text-red-700 text-xs font-bold rounded-full">
          {openCount} ouvert{openCount > 1 ? 's' : ''}
        </span>
      )}

      {/* Filtres */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => { setFilter(f.value); setSelected(null) }}
            className="px-4 py-1.5 rounded-full text-sm font-medium transition-all"
            style={{
              background: filter === f.value ? '#0D2F5C' : '#F1F5F9',
              color: filter === f.value ? '#FFFFFF' : '#475569',
            }}
          >
            {f.label}
          </button>
        ))}
        <span className="ml-auto text-sm text-gray-400 self-center">{total} ticket{total > 1 ? 's' : ''}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Liste */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {isLoading ? (
              <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
            ) : tickets.length === 0 ? (
              <div className="py-12 text-center">
                <MessageSquare size={32} className="mx-auto mb-2 text-gray-300" />
                <p className="text-sm text-gray-400">Aucun ticket</p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {tickets.map(ticket => {
                  const sc = STATUS_CONFIG[ticket.status] ?? STATUS_CONFIG.open
                  const pc = PRIORITY_CONFIG[ticket.priority]
                  const Icon = sc.icon
                  return (
                    <li key={ticket.id}>
                      <button
                        onClick={() => loadDetail(ticket.id)}
                        className={`w-full text-left px-4 py-3.5 hover:bg-gray-50 transition-colors ${selected?.id === ticket.id ? 'bg-blue-50 border-l-2 border-blue-500' : ''}`}
                      >
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <p className="text-sm font-medium text-gray-900 truncate flex-1">{ticket.title}</p>
                          <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0"
                            style={{ color: sc.color, background: sc.bg }}>
                            <Icon size={9} />
                            {sc.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span className="flex items-center gap-1 px-1.5 py-0.5 bg-teal-50 text-teal-700 rounded text-xs font-medium">
                            <User size={9} /> Locataire
                          </span>
                          <span className="truncate">{ticket.tenant_name}</span>
                          <span className="text-gray-300">·</span>
                          <span style={{ color: pc.color }}>{pc.label}</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {format(new Date(ticket.created_at), 'd MMM yyyy', { locale: fr })}
                        </p>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>

        {/* Détail */}
        <div className="lg:col-span-3">
          {!selected ? (
            <div className="bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center h-64">
              <MessageSquare size={36} className="text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Sélectionnez un ticket pour voir les détails</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 flex flex-col" style={{ minHeight: '420px' }}>
              {/* Header */}
              <div className="px-5 py-4 border-b border-gray-100">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">{selected.title}</h3>
                    <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-gray-500">
                      <span className="flex items-center gap-1 px-1.5 py-0.5 bg-teal-50 text-teal-700 rounded font-medium">
                        <User size={9} /> Locataire
                      </span>
                      <span>{selected.tenant_name}</span>
                      <span className="text-gray-300">·</span>
                      <span>{CATEGORY_LABELS[selected.category]}</span>
                      <span className="text-gray-300">·</span>
                      <span style={{ color: PRIORITY_CONFIG[selected.priority]?.color }}>
                        {PRIORITY_CONFIG[selected.priority]?.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {readOnly ? (
                      (() => {
                        const sc = STATUS_CONFIG[newStatus] ?? STATUS_CONFIG.open
                        const Icon = sc.icon
                        return (
                          <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full flex-shrink-0"
                            style={{ color: sc.color, background: sc.bg }}>
                            <Icon size={11} />{sc.label}
                          </span>
                        )
                      })()
                    ) : (
                      <select
                        value={newStatus}
                        onChange={e => handleStatusChange(e.target.value)}
                        className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white"
                        style={{ color: STATUS_CONFIG[newStatus]?.color }}
                      >
                        {Object.entries(STATUS_CONFIG).map(([value, cfg]) => (
                          <option key={value} value={value}>{cfg.label}</option>
                        ))}
                      </select>
                    )}
                    {statusError && (
                      <p className="text-xs text-red-600 max-w-[180px] text-right">{statusError}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
                {(selected.messages ?? [])
                  .filter(m => !m.is_internal)
                  .map(msg => {
                    const isStaff = msg.author_role !== 'locataire'
                    const roleLabel = msg.author_role === 'locataire' ? 'Locataire'
                      : msg.author_role === 'proprietaire' ? 'Propriétaire'
                      : 'Gestionnaire'
                    const roleColor = msg.author_role === 'locataire'
                      ? 'bg-teal-100 text-teal-700'
                      : msg.author_role === 'proprietaire'
                      ? 'bg-orange-100 text-orange-700'
                      : 'bg-blue-100 text-blue-700'
                    return (
                      <div key={msg.id} className={`flex ${isStaff ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-xl px-4 py-3 ${isStaff ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-xs font-semibold opacity-70">
                              {msg.author_name ?? roleLabel}
                            </p>
                            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${isStaff ? 'bg-white/20 text-white' : roleColor}`}>
                              {roleLabel}
                            </span>
                          </div>
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          <p className="text-xs mt-1.5 opacity-60">
                            {format(new Date(msg.created_at), 'dd/MM/yyyy HH:mm')}
                          </p>
                        </div>
                      </div>
                    )
                  })}
              </div>

              {/* Réponse */}
              {!readOnly && selected.status !== 'closed' && (
                <div className="px-5 py-4 border-t border-gray-100">
                  <div className="flex gap-3">
                    <textarea
                      value={reply}
                      onChange={e => setReply(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleReply() } }}
                      placeholder="Répondre au locataire… (Entrée pour envoyer)"
                      rows={2}
                      className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm resize-none focus:outline-none focus:border-blue-400"
                    />
                    <button
                      onClick={handleReply}
                      disabled={isSending || !reply.trim()}
                      className="px-4 rounded-xl text-white disabled:opacity-40"
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
    </div>
  )
}

// ── Composant onglet messages propriétaires ─────────────────────────────────────

function ProprietaireMessagesTab() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<ProprietaireMessage[]>([])
  const [isLoadingConvs, setIsLoadingConvs] = useState(true)
  const [isLoadingMsgs, setIsLoadingMsgs] = useState(false)
  const [reply, setReply] = useState('')
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const loadConversations = async () => {
    setIsLoadingConvs(true)
    try {
      const res = await messagesApi.list()
      const convs = res.data.conversations ?? []
      setConversations(convs)
    } catch { /* */ }
    finally { setIsLoadingConvs(false) }
  }

  const loadMessages = async (proprietaireId: string) => {
    setIsLoadingMsgs(true)
    try {
      const res = await messagesApi.list(proprietaireId)
      setMessages(res.data.messages ?? [])
    } catch { /* */ }
    finally {
      setIsLoadingMsgs(false)
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  useEffect(() => { loadConversations() }, [])

  const handleSelectConv = (conv: Conversation) => {
    setSelectedConv(conv)
    loadMessages(conv.proprietaire_id)
  }

  const handleSend = async () => {
    if (!reply.trim() || !selectedConv) return
    setIsSending(true)
    try {
      await messagesApi.send(reply, selectedConv.proprietaire_id)
      setReply('')
      await loadMessages(selectedConv.proprietaire_id)
      await loadConversations()
    } finally { setIsSending(false) }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      {/* Liste conversations */}
      <div className="lg:col-span-2">
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Propriétaires</p>
          </div>
          {isLoadingConvs ? (
            <div className="py-12 text-center text-gray-400 text-sm">Chargement…</div>
          ) : conversations.length === 0 ? (
            <div className="py-12 text-center">
              <Building2 size={32} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm text-gray-400">Aucune conversation</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {conversations.map(conv => (
                <li key={conv.proprietaire_id}>
                  <button
                    onClick={() => handleSelectConv(conv)}
                    className={`w-full text-left px-4 py-3.5 hover:bg-gray-50 transition-colors ${
                      selectedConv?.proprietaire_id === conv.proprietaire_id ? 'bg-orange-50 border-l-2 border-orange-400' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <p className="text-sm font-medium text-gray-900 truncate">{conv.proprietaire_name}</p>
                          <span className="flex-shrink-0 text-xs px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded font-medium">
                            Proprio
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 truncate">{conv.last_message}</p>
                      </div>
                      {conv.unread_count > 0 && (
                        <span className="flex-shrink-0 px-1.5 py-0.5 bg-orange-500 text-white text-xs font-bold rounded-full">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                    {conv.last_message_at && (
                      <p className="text-xs text-gray-400 mt-1">
                        {format(new Date(conv.last_message_at), 'd MMM yyyy HH:mm', { locale: fr })}
                      </p>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Thread messages */}
      <div className="lg:col-span-3">
        {!selectedConv ? (
          <div className="bg-white rounded-xl border border-gray-200 flex flex-col items-center justify-center h-64">
            <Building2 size={36} className="text-gray-200 mb-3" />
            <p className="text-sm text-gray-400">Sélectionnez un propriétaire pour voir la conversation</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 flex flex-col" style={{ minHeight: '420px' }}>
            <div className="px-5 py-4 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">{selectedConv.proprietaire_name}</span>
                <span className="text-xs px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded font-medium">Proprio</span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {isLoadingMsgs ? (
                <p className="text-sm text-gray-400 text-center">Chargement…</p>
              ) : messages.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">Aucun message</p>
              ) : (
                messages.map(msg => {
                  const isGest = msg.is_from_gestionnaire
                  const roleLabel = isGest ? 'Gestionnaire' : 'Proprio'
                  const roleColor = isGest ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'
                  return (
                    <div key={msg.id} className={`flex ${isGest ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-xl px-4 py-3 ${isGest ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-xs font-semibold opacity-70">{msg.sender_name ?? roleLabel}</p>
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${isGest ? 'bg-white/20 text-white' : roleColor}`}>
                            {roleLabel}
                          </span>
                        </div>
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        <p className="text-xs mt-1.5 opacity-60">
                          {format(new Date(msg.created_at), 'dd/MM/yyyy HH:mm')}
                        </p>
                      </div>
                    </div>
                  )
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="px-5 py-4 border-t border-gray-100">
              <div className="flex gap-3">
                <textarea
                  value={reply}
                  onChange={e => setReply(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
                  placeholder={`Message à ${selectedConv.proprietaire_name}… (Entrée pour envoyer)`}
                  rows={2}
                  className="flex-1 border border-gray-200 rounded-xl px-3 py-2.5 text-sm resize-none focus:outline-none focus:border-blue-400"
                />
                <button
                  onClick={handleSend}
                  disabled={isSending || !reply.trim()}
                  className="px-4 rounded-xl text-white disabled:opacity-40"
                  style={{ background: '#0D2F5C' }}
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Page principale ─────────────────────────────────────────────────────────────

export default function IncidentList({
  readOnly = false,
  fetchFn,
  title = 'Incidents & messages',
  subtitle = 'Messages et demandes des locataires',
  hideProprietaireTab = false,
}: {
  readOnly?: boolean
  fetchFn?: FetchFn
  title?: string
  subtitle?: string
  hideProprietaireTab?: boolean
}) {
  const { user } = useAuthStore()
  const isGestionnairePropio = user?.role === 'gestionnaire_proprio'
  const showProprietaireTab = !hideProprietaireTab && !isGestionnairePropio

  const [activeTab, setActiveTab] = useState<'tickets' | 'messages'>('tickets')

  return (
    <div className="p-6">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        <p className="text-gray-500 text-sm mt-1">{subtitle}</p>
      </div>

      {/* Onglets — visibles uniquement si l'onglet proprio est pertinent */}
      {!readOnly && showProprietaireTab && (
        <div className="flex gap-1 mb-6 bg-gray-100 rounded-xl p-1 w-fit">
          <button
            onClick={() => setActiveTab('tickets')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'tickets'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <MessageSquare size={15} />
            Tickets locataires
          </button>
          <button
            onClick={() => setActiveTab('messages')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'messages'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Building2 size={15} />
            Messages propriétaires
          </button>
        </div>
      )}

      {/* Contenu selon onglet */}
      {(readOnly || !showProprietaireTab || activeTab === 'tickets') && (
        <TicketsTab readOnly={readOnly} fetchFn={fetchFn} />
      )}
      {!readOnly && showProprietaireTab && activeTab === 'messages' && (
        <ProprietaireMessagesTab />
      )}
    </div>
  )
}
