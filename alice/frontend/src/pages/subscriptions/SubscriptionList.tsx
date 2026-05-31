import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Inbox, Mail, Phone, Building2, Check, Clock, X, Trash2, RotateCcw } from 'lucide-react'
import { subscriptionsApi, type SubscriptionRequest } from '@/api/subscriptions'

const STATUS = {
  nouveau:  { label: 'Nouveau',   cls: 'bg-blue-100 text-blue-700' },
  en_cours: { label: 'En cours',  cls: 'bg-amber-100 text-amber-700' },
  traite:   { label: 'Traité',    cls: 'bg-green-100 text-green-700' },
  rejete:   { label: 'Rejeté',    cls: 'bg-gray-100 text-gray-500' },
} as const

const FILTERS: { key: string; label: string }[] = [
  { key: '', label: 'Toutes' },
  { key: 'nouveau', label: 'Nouvelles' },
  { key: 'en_cours', label: 'En cours' },
  { key: 'traite', label: 'Traitées' },
  { key: 'rejete', label: 'Rejetées' },
]

function fmt(iso: string) {
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
}

export default function SubscriptionList() {
  const [items, setItems] = useState<SubscriptionRequest[]>([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (status: string) => {
    setLoading(true)
    try {
      const { data } = await subscriptionsApi.list(status || undefined)
      setItems(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(filter) }, [filter, load])

  const setStatus = async (id: string, status: string) => {
    await subscriptionsApi.update(id, { status })
    load(filter)
  }

  const navigate = useNavigate()

  const handleDeactivate = async (r: SubscriptionRequest) => {
    if (!window.confirm(
      `Désactiver le compte de ${r.full_name} ?\n\nL'accès est maintenu jusqu'à la fin du mois de facturation en cours, puis le compte est bloqué automatiquement.`
    )) return
    try {
      const { data } = await subscriptionsApi.deactivateAccount(r.id)
      if (!data.found_account) {
        window.alert('Aucun compte gestionnaire trouvé pour cet email. La demande est marquée traitée.')
      } else if (data.scheduled_until) {
        window.alert(`Désactivation programmée le ${new Date(data.scheduled_until).toLocaleDateString('fr-FR')} (accès maintenu jusque-là).`)
      } else if (data.blocked_now) {
        window.alert('Compte bloqué immédiatement.')
      }
      load(filter)
    } catch {
      window.alert('Échec de la désactivation.')
    }
  }

  const handleReactivate = async (r: SubscriptionRequest) => {
    if (!window.confirm(
      `Réactiver le compte de ${r.full_name} ?\n\nLa désactivation programmée est annulée et le compte est débloqué s'il l'était déjà.`
    )) return
    try {
      const { data } = await subscriptionsApi.reactivateAccount(r.id)
      if (!data.found_account) {
        window.alert('Aucun compte gestionnaire trouvé pour cet email.')
      } else if (data.reactivated) {
        window.alert('Compte réactivé : la désactivation a été annulée.')
      } else {
        window.alert('Aucune désactivation en cours pour ce compte.')
      }
      load(filter)
    } catch {
      window.alert('Échec de la réactivation.')
    }
  }

  const handleCreateAccount = (r: SubscriptionRequest) => {
    navigate('/gestionnaires', { state: { prefill: { full_name: r.full_name, email: r.email } } })
  }

  const handleDelete = async (r: SubscriptionRequest) => {
    if (!window.confirm(`Supprimer définitivement cette demande de ${r.full_name} ?`)) return
    try {
      await subscriptionsApi.remove(r.id)
      load(filter)
    } catch {
      window.alert('Échec de la suppression.')
    }
  }

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Inbox size={24} className="text-gray-700" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Demandes de souscription et de résiliation</h1>
          <p className="text-sm text-gray-500">Souscriptions (page d'accueil) et demandes de résiliation (espaces gestionnaires)</p>
        </div>
      </div>

      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {FILTERS.map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              filter === f.key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
            }`}>
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {loading ? (
          <div className="p-10 text-center text-gray-400 text-sm">Chargement…</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <Inbox size={40} className="mx-auto mb-3 opacity-40" />
            <p className="font-medium">Aucune demande</p>
          </div>
        ) : (
          <table className="w-full text-sm min-w-[720px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Demandeur</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Coordonnées</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Besoin</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Reçue le</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Statut</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(r => (
                <tr key={r.id} className="hover:bg-gray-50 align-top">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900 flex items-center gap-2">
                      {r.full_name}
                      {r.source === 'resiliation' && (
                        <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-red-100 text-red-700">Résiliation</span>
                      )}
                    </p>
                    {r.company && (
                      <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                        <Building2 size={11} /> {r.company}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    <p className="flex items-center gap-1.5"><Mail size={12} className="text-gray-400" /> {r.email}</p>
                    {r.phone && <p className="flex items-center gap-1.5 mt-0.5"><Phone size={12} className="text-gray-400" /> {r.phone}</p>}
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs">
                    {r.message ? <span className="line-clamp-3">{r.message}</span> : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{fmt(r.created_at)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS[r.status].cls}`}>
                      {STATUS[r.status].label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {r.status !== 'traite' && r.source === 'resiliation' && (
                        <button onClick={() => handleDeactivate(r)}
                          className="px-2 py-1 text-xs font-medium rounded border border-red-300 text-red-600 hover:bg-red-50 transition-colors whitespace-nowrap">
                          Désactiver le compte
                        </button>
                      )}
                      {r.status === 'traite' && r.source === 'resiliation' && (
                        <button onClick={() => handleReactivate(r)}
                          className="px-2 py-1 text-xs font-medium rounded border border-emerald-300 text-emerald-600 hover:bg-emerald-50 transition-colors whitespace-nowrap inline-flex items-center gap-1">
                          <RotateCcw size={12} /> Réactiver
                        </button>
                      )}
                      {r.status !== 'traite' && r.source !== 'resiliation' && (
                        <button onClick={() => handleCreateAccount(r)}
                          className="px-2 py-1 text-xs font-medium rounded border border-indigo-300 text-indigo-600 hover:bg-indigo-50 transition-colors whitespace-nowrap">
                          Créer un compte
                        </button>
                      )}
                      {r.status !== 'en_cours' && (
                        <button onClick={() => setStatus(r.id, 'en_cours')} title="Marquer en cours"
                          className="p-1.5 rounded hover:bg-amber-50 text-gray-400 hover:text-amber-600"><Clock size={15} /></button>
                      )}
                      {r.status !== 'traite' && (
                        <button onClick={() => setStatus(r.id, 'traite')} title="Marquer traité"
                          className="p-1.5 rounded hover:bg-green-50 text-gray-400 hover:text-green-600"><Check size={15} /></button>
                      )}
                      {r.status !== 'rejete' && (
                        <button onClick={() => setStatus(r.id, 'rejete')} title="Rejeter"
                          className="p-1.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-600"><X size={15} /></button>
                      )}
                      <button onClick={() => handleDelete(r)} title="Supprimer la demande"
                        className="p-1.5 rounded hover:bg-red-100 text-gray-400 hover:text-red-700"><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
