import { useCallback, useEffect, useState } from 'react'
import { Button, Spinner } from '@/components/ui'
import { auditApi, type AuditLog } from '@/api/audit'

// Libellés lisibles des actions et des entités (tables) du journal.
const ACTION_LABEL: Record<string, string> = {
  'db.create': 'Création',
  'db.update': 'Modification',
  'db.delete': 'Suppression',
}
const ACTION_CLASS: Record<string, string> = {
  'db.create': 'bg-emerald-50 text-emerald-700',
  'db.update': 'bg-amber-50 text-amber-700',
  'db.delete': 'bg-red-50 text-red-700',
}
const ENTITY_LABEL: Record<string, string> = {
  properties: 'Bien',
  tenants: 'Locataire',
  owners: 'Propriétaire',
  leases: 'Bail',
  payments: 'Paiement',
  payment_adjustments: 'Ajustement',
  lease_rent_revisions: 'Révision de loyer',
  inspections: 'État des lieux',
  lease_exits: 'Sortie',
  documents: 'Document',
  tickets: 'Demande',
  signalements: 'Signalement',
  entretiens: 'Entretien',
  contacts: 'Contact',
  users: 'Utilisateur',
  message_templates: 'Modèle e-mail',
  communication_rules: 'Règle de communication',
}

const FILTERS: { key: string; label: string }[] = [
  { key: '', label: 'Toutes' },
  { key: 'db.create', label: 'Créations' },
  { key: 'db.update', label: 'Modifications' },
  { key: 'db.delete', label: 'Suppressions' },
]

const PAGE = 100

function fmt(iso: string) {
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function AuditPage() {
  const [rows, setRows] = useState<AuditLog[] | null>(null)
  const [action, setAction] = useState('')
  const [search, setSearch] = useState('')
  const [loadingMore, setLoadingMore] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (reset = true) => {
    setError(null)
    if (reset) { setRows(null); setDone(false) }
    const skip = reset ? 0 : (rows?.length ?? 0)
    try {
      const { data } = await auditApi.list({
        action: action || undefined,
        user_email: search.trim() || undefined,
        limit: PAGE,
        skip,
      })
      setRows((prev) => (reset || !prev ? data : [...prev, ...data]))
      setDone(data.length < PAGE)
    } catch {
      setError("Impossible de charger le journal d'audit. Réessayez.")
      if (reset) setRows([])
    }
  }, [action, search, rows])

  // Recharge à chaque changement de filtre d'action.
  useEffect(() => { load(true) /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [action])

  const more = async () => { setLoadingMore(true); await load(false); setLoadingMore(false) }

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="mb-1 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Audit</h1>
      </div>
      <p className="mb-5 text-sm text-gray-500">
        Journal des actions de votre agence : vous, vos comptables, vos propriétaires et vos
        locataires. Les autres agences ne sont jamais visibles.
      </p>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setAction(f.key)}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              action === f.key
                ? 'bg-brand-navy text-white border-brand-navy'
                : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
            }`}
          >
            {f.label}
          </button>
        ))}
        <form
          onSubmit={(e) => { e.preventDefault(); load(true) }}
          className="ml-auto flex items-center gap-2"
        >
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher par e-mail…"
            className="w-56 px-3 py-1.5 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          />
          <Button type="submit" variant="secondary">Rechercher</Button>
        </form>
      </div>

      {error && (
        <div className="mb-4 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {!rows ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
          Aucune action enregistrée.
        </div>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm min-w-[680px]">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700">Date</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700">Auteur</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700">Action</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700">Élément</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 align-top">
                    <td className="px-4 py-2.5 whitespace-nowrap text-gray-500 text-xs">{fmt(r.created_at)}</td>
                    <td className="px-4 py-2.5 text-gray-700">{r.user_email ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${ACTION_CLASS[r.action] ?? 'bg-gray-100 text-gray-600'}`}>
                        {ACTION_LABEL[r.action] ?? r.action}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">
                      {r.entity_type ? (ENTITY_LABEL[r.entity_type] ?? r.entity_type) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!done && (
            <div className="mt-4 text-center">
              <Button variant="secondary" onClick={more} disabled={loadingMore}>
                {loadingMore ? 'Chargement…' : 'Charger plus'}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
