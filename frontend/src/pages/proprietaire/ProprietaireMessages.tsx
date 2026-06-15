import { useState, useEffect, useRef } from 'react'
import { BRAND } from '@/lib/brand'
import { MessageSquare, Send, Building2 } from 'lucide-react'
import { messagesApi, type ProprietaireMessage } from '@/api/messages'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

export default function ProprietaireMessages() {
  const [messages, setMessages] = useState<ProprietaireMessage[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [text, setText] = useState('')
  const [isSending, setIsSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const load = async () => {
    try {
      const res = await messagesApi.list()
      setMessages(res.data.messages ?? [])
    } catch {
      setMessages([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const trimmed = text.trim()
    if (!trimmed || isSending) return
    setIsSending(true)
    try {
      const res = await messagesApi.send(trimmed)
      setMessages(prev => [...prev, res.data])
      setText('')
    } catch { /* */ }
    finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
            <MessageSquare size={20} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Messages</h1>
            <p className="text-sm text-gray-500">Communication avec votre gestionnaire</p>
          </div>
        </div>
      </div>

      {/* Chat window */}
      <div className="bg-white rounded-xl border border-gray-200 flex flex-col" style={{ height: '60vh' }}>
        {/* Conversation header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
          <div className="w-9 h-9 bg-gray-800 rounded-full flex items-center justify-center">
            <Building2 size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Votre gestionnaire</p>
            <p className="text-xs text-green-500">En ligne</p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              Chargement…
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <MessageSquare size={40} className="text-gray-200 mb-3" />
              <p className="text-sm font-medium text-gray-500">Aucun message pour l'instant</p>
              <p className="text-xs mt-1">Envoyez votre premier message à votre gestionnaire</p>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => {
                const isMe = !msg.is_from_gestionnaire
                const showDate =
                  i === 0 ||
                  format(new Date(messages[i - 1].created_at), 'dd/MM/yyyy') !==
                    format(new Date(msg.created_at), 'dd/MM/yyyy')

                return (
                  <div key={msg.id}>
                    {showDate && (
                      <div className="flex items-center gap-2 my-3">
                        <div className="flex-1 h-px bg-gray-100" />
                        <span className="text-xs text-gray-400 px-2">
                          {format(new Date(msg.created_at), 'd MMMM yyyy', { locale: fr })}
                        </span>
                        <div className="flex-1 h-px bg-gray-100" />
                      </div>
                    )}
                    <div className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                      <div className="max-w-[75%]">
                        <div
                          className={`rounded-2xl px-4 py-3 text-sm ${
                            isMe
                              ? 'bg-blue-600 text-white rounded-br-sm'
                              : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                          }`}
                        >
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        </div>
                        <p className={`text-xs text-gray-400 mt-1 ${isMe ? 'text-right' : 'text-left'}`}>
                          {format(new Date(msg.created_at), 'HH:mm')}
                          {!isMe && msg.sender_name && (
                            <span className="ml-1 text-gray-500">· {msg.sender_name}</span>
                          )}
                        </p>
                      </div>
                    </div>
                  </div>
                )
              })}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="px-5 py-4 border-t border-gray-100">
          <div className="flex items-end gap-3">
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Écrivez votre message… (Entrée pour envoyer)"
              rows={2}
              className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={isSending || !text.trim()}
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white transition-all disabled:opacity-40"
              style={{ background: BRAND.navy }}
            >
              <Send size={16} />
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">Entrée pour envoyer · Maj+Entrée pour aller à la ligne</p>
        </div>
      </div>
    </div>
  )
}
