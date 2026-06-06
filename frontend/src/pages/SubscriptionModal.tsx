import { useState } from 'react'
import { X, Send, CheckCircle } from 'lucide-react'
import { apiClient } from '@/api/client'

interface Props {
  open: boolean
  onClose: () => void
}

/** Demande de souscription / démo — page d'accueil. Alimente Alice (lead à traiter). */
export default function SubscriptionModal({ open, onClose }: Props) {
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', phone: '', company: '', message: '' })
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    const fullName = `${form.first_name.trim()} ${form.last_name.trim()}`.trim()
    if (!form.first_name.trim() || !form.last_name.trim() || !form.email.includes('@')) {
      setError('Prénom, nom et email valides requis.')
      return
    }
    if (form.phone.trim().length < 6) {
      setError('Un numéro de téléphone est requis.')
      return
    }
    setSending(true); setError(null)
    try {
      await apiClient.post('/public/subscription-requests', {
        full_name: fullName,
        email: form.email.trim(),
        phone: form.phone.trim(),
        company: form.company || null,
        message: form.message || null,
      })
      setDone(true)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Une erreur est survenue. Réessayez plus tard.")
    } finally {
      setSending(false)
    }
  }

  const inp = 'w-full px-3 py-2.5 text-sm rounded-xl outline-none border border-gray-200 bg-gray-50 focus:bg-white focus:border-[#0D2F5C] focus:ring-2 focus:ring-[#0D2F5C]/10 transition-all'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100"
             style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}>
          <h2 className="text-base font-semibold text-white">Demander une démo</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-white/80">
            <X size={16} />
          </button>
        </div>

        {done ? (
          <div className="px-6 py-10 text-center">
            <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={28} className="text-green-600" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">Demande envoyée</h3>
            <p className="text-sm text-gray-500 mb-5">
              Merci ! Notre équipe vous recontacte rapidement pour la mise en place de votre espace.
            </p>
            <button onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white rounded-xl"
              style={{ background: '#0D2F5C' }}>
              Fermer
            </button>
          </div>
        ) : (
          <div className="px-6 py-5 space-y-3">
            <p className="text-sm text-gray-500">
              Vous gérez des biens en location ? Laissez-nous vos coordonnées, on s'occupe du reste.
            </p>
            {error && (
              <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
            )}
            <div className="grid grid-cols-1 gap-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input className={inp} placeholder="Prénom *" value={form.first_name}
                  onChange={e => set('first_name', e.target.value)} />
                <input className={inp} placeholder="Nom *" value={form.last_name}
                  onChange={e => set('last_name', e.target.value)} />
              </div>
              <input className={inp} placeholder="Email professionnel *" type="email" value={form.email}
                onChange={e => set('email', e.target.value)} />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input className={inp} placeholder="Téléphone *" value={form.phone}
                  onChange={e => set('phone', e.target.value)} />
                <input className={inp} placeholder="Société / agence" value={form.company}
                  onChange={e => set('company', e.target.value)} />
              </div>
              <textarea className={`${inp} resize-none`} rows={3} placeholder="Votre besoin (optionnel)"
                value={form.message} onChange={e => set('message', e.target.value)} />
            </div>
            <button onClick={submit} disabled={sending}
              className="w-full py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-60"
              style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}>
              <Send size={15} /> {sending ? 'Envoi…' : 'Envoyer ma demande'}
            </button>
            <p className="text-[11px] text-gray-400 text-center">
              Vos données ne servent qu'à vous recontacter. Aucun engagement.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
