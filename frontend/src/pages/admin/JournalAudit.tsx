import { useEffect, useState } from 'react'
import { ShieldCheck, RefreshCw } from 'lucide-react'
import { apiClient } from '@/api/client'

interface AuditLog {
  id: string
  created_at: string
  user_email: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  ip_address: string | null
  details: unknown
}

const ACTION_LABELS: Record<string, string> = {
  login: 'Connexion', login_failed: 'Connexion échouée',
  'rgpd.export': 'RGPD — export', 'rgpd.erase': 'RGPD — effacement',
  'rgpd.retention': 'RGPD — rétention', 'payment.record': 'Paiement enregistré',
  'payment.card_paid': 'Paiement par carte', 'payment.delete': 'Paiement supprimé',
  'lease.create': 'Bail créé', 'lease.terminate': 'Bail résilié',
  'user.create': 'Compte créé', 'user.block': 'Compte bloqué', 'user.unblock': 'Compte débloqué',
  'document.upload': 'Document ajouté', 'document.delete': 'Document supprimé',
}

export default function JournalAudit() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [action, setAction] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true); setError('')
    apiClient.get<AuditLog[]>('/audit', { params: { action: action || undefined, limit: 100 } })
      .then((r) => setLogs(r.data))
      .catch(() => setError("Impossible de charger le journal d'audit."))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <ShieldCheck className="text-[#0D2F5C]" size={24} />
        <h1 className="text-2xl font-bold text-gray-900">Journal d'audit</h1>
      </div>
      <p className="text-gray-500 text-sm mb-6">Traçabilité des actions sensibles (qui, quoi, quand).</p>

      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Filtrer par action</label>
          <input value={action} onChange={(e) => setAction(e.target.value)}
            placeholder="ex. rgpd.export"
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-56" />
        </div>
        <button onClick={load}
          className="inline-flex items-center gap-2 bg-[#0D2F5C] text-white rounded-lg px-3 py-2 text-sm">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Actualiser
        </button>
      </div>

      {error && <div className="mb-4 text-sm text-red-700 bg-red-50 rounded-lg px-3 py-2">{error}</div>}

      <div className="bg-white border border-gray-200 rounded-xl overflow-x-auto shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left text-xs uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Utilisateur</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Cible</th>
              <th className="px-4 py-3 font-medium">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {logs.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-10 text-center text-gray-400">
                {loading ? 'Chargement…' : 'Aucune entrée'}
              </td></tr>
            ) : logs.map((l) => (
              <tr key={l.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 whitespace-nowrap">{new Date(l.created_at).toLocaleString('fr-FR')}</td>
                <td className="px-4 py-2.5">{l.user_email || '—'}</td>
                <td className="px-4 py-2.5">{ACTION_LABELS[l.action] || l.action}</td>
                <td className="px-4 py-2.5 text-gray-500">{l.entity_type || '—'}</td>
                <td className="px-4 py-2.5 text-gray-400 text-xs">{l.ip_address || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
