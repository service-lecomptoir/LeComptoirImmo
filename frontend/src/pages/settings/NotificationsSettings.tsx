import { useState, useEffect, type ReactNode } from 'react'
import { Mail, MessageSquare, Send, CheckCircle, XCircle, Copy } from 'lucide-react'
import { apiClient } from '@/api/client'
import { toast } from '@/store/toast'

interface Status {
  email_enabled: boolean
  sms_enabled: boolean
  smtp_from: string
  sms_sender: string
  cc_manager_emails: boolean
}

export default function NotificationsSettings({ embedded = false }: { embedded?: boolean }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [loading, setLoading] = useState(true)
  const [channel, setChannel] = useState<'email' | 'sms'>('email')
  const [to, setTo] = useState('')
  const [sending, setSending] = useState(false)

  const load = () => {
    setLoading(true)
    apiClient.get<Status>('/settings/notifications-status')
      .then(r => setStatus(r.data))
      .catch(() => { })
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const [ccSaving, setCcSaving] = useState(false)
  const toggleCc = async () => {
    if (!status) return
    const next = !status.cc_manager_emails
    setCcSaving(true)
    try {
      await apiClient.put('/settings/cc-manager', { enabled: next })
      setStatus({ ...status, cc_manager_emails: next })
      toast.success(next
        ? 'Le gestionnaire sera mis en copie des e-mails locataires.'
        : 'Le gestionnaire ne sera plus mis en copie.')
    } catch {
      toast.error('Impossible de modifier ce réglage.')
    } finally {
      setCcSaving(false)
    }
  }

  const sendTest = async () => {
    if (!to.trim()) { toast.error('Indiquez un destinataire.'); return }
    setSending(true)
    try {
      const { data } = await apiClient.post('/settings/test-notification', { channel, to: to.trim() })
      if (data.sent) toast.success(`Test ${channel === 'email' ? 'e-mail' : 'SMS'} envoyé à ${to.trim()}.`)
      else toast.error(data.detail || 'Envoi non effectué (canal désactivé ou erreur).')
    } catch {
      toast.error('Erreur lors de l\'envoi du test.')
    } finally {
      setSending(false)
    }
  }

  const StatusRow = ({ icon, label, enabled, detail }: { icon: ReactNode; label: string; enabled: boolean; detail?: string }) => (
    <div className="flex items-center justify-between gap-3 py-3">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl bg-gray-50 flex items-center justify-center shrink-0">{icon}</div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900">{label}</p>
          {detail && <p className="text-xs text-gray-400 truncate">{detail}</p>}
        </div>
      </div>
      {enabled ? (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2.5 py-1">
          <CheckCircle size={13} /> Actif
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 bg-gray-50 border border-gray-200 rounded-full px-2.5 py-1">
          <XCircle size={13} /> Inactif
        </span>
      )}
    </div>
  )

  return (
    <div className={embedded ? 'max-w-2xl' : 'p-4 sm:p-6 max-w-2xl'}>
      {!embedded && (
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-gray-500 text-sm mt-1">État des canaux e-mail / SMS et envoi de tests.</p>
        </div>
      )}

      {/* État des canaux */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5 divide-y divide-gray-100">
        {loading ? (
          <p className="text-sm text-gray-400 py-6 text-center">Chargement…</p>
        ) : status ? (
          <>
            <StatusRow icon={<Mail size={18} className="text-blue-600" />} label="E-mail (SMTP)"
              enabled={status.email_enabled} detail={status.smtp_from ? `Expéditeur : ${status.smtp_from}` : undefined} />
            <StatusRow icon={<MessageSquare size={18} className="text-emerald-600" />} label="SMS"
              enabled={status.sms_enabled} detail={status.sms_sender ? `Expéditeur : ${status.sms_sender}` : undefined} />
          </>
        ) : (
          <p className="text-sm text-gray-400 py-6 text-center">État indisponible.</p>
        )}
      </div>

      {/* Mise en copie du gestionnaire */}
      {status && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-gray-50 flex items-center justify-center shrink-0">
                <Copy size={18} className="text-indigo-600" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900">Gestionnaire en copie (CC)</p>
                <p className="text-xs text-gray-400">
                  Met le gestionnaire en copie des e-mails envoyés aux locataires (avis, quittances, relances, communications).
                </p>
              </div>
            </div>
            <button onClick={toggleCc} disabled={ccSaving} role="switch" aria-checked={status.cc_manager_emails}
              className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${status.cc_manager_emails ? 'bg-indigo-600' : 'bg-gray-300'}`}>
              <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${status.cc_manager_emails ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
        </div>
      )}

      {/* Envoi d'un test */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <p className="text-sm font-semibold text-gray-800 mb-3">Envoyer un test</p>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex rounded-lg border border-gray-200 overflow-hidden shrink-0">
            <button onClick={() => setChannel('email')}
              className={`px-3 py-2 text-sm font-medium ${channel === 'email' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600'}`}>
              E-mail
            </button>
            <button onClick={() => setChannel('sms')}
              className={`px-3 py-2 text-sm font-medium ${channel === 'sms' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600'}`}>
              SMS
            </button>
          </div>
          <input
            value={to} onChange={e => setTo(e.target.value)}
            placeholder={channel === 'email' ? 'adresse@exemple.fr' : '06 12 34 56 78'}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onClick={sendTest} disabled={sending}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 shrink-0"
            style={{ background: '#0D2F5C' }}>
            <Send size={15} /> {sending ? 'Envoi…' : 'Tester'}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Le canal doit être « Actif » ci-dessus. La configuration (clés Brevo) se fait côté serveur.
        </p>
      </div>
    </div>
  )
}
