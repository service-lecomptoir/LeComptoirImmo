import { useEffect, useState } from 'react'
import { Store, ExternalLink } from 'lucide-react'
import { apiClient } from '@/api/client'
import { Button, Input } from '@/components/ui'

interface Props {
  kind: 'property' | 'copropriete'
  id: string
}

interface LinkState {
  linked: boolean
  boutique_url?: string | null
}

interface ManagerBoutique {
  id: string
  slug?: string | null
  nom?: string | null
  url?: string | null
}

/**
 * Pont Le Comptoir Market : carte « Boutique de la résidence » sur le détail d'un
 * bien ou d'une copropriété. Le gestionnaire rattache la résidence à une boutique
 * existante (UNE boutique peut servir plusieurs biens) ou en crée une nouvelle.
 * Si Le Comptoir Market n'est pas activé pour le compte, affiche une CTA.
 */
export default function ResidenceBoutiqueCard({ kind, id }: Props) {
  const [state, setState] = useState<LinkState | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [marketAbsent, setMarketAbsent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Boutiques de résidence déjà créées par le gestionnaire (pour rattacher).
  const [boutiques, setBoutiques] = useState<ManagerBoutique[]>([])
  // '' = créer une nouvelle boutique ; sinon = id de la boutique à rattacher.
  const [choice, setChoice] = useState<string>('')
  const [newName, setNewName] = useState('')

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([
      apiClient.get(`/residences/${kind}/${id}/boutique`).then((r) => r.data),
      apiClient
        .get('/residences/my-manager-boutiques')
        .then((r) => r.data)
        .catch(() => ({ market_enabled: true, boutiques: [] })),
    ])
      .then(([link, mine]) => {
        if (!alive) return
        setState(link)
        setBoutiques(mine.boutiques || [])
        // Par défaut : rattacher à la première boutique existante s'il y en a.
        if (mine.boutiques && mine.boutiques.length > 0) setChoice(mine.boutiques[0].id)
      })
      .catch(() => { if (alive) setState({ linked: false }) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [kind, id])

  const deploy = async () => {
    setWorking(true)
    setError(null)
    setMarketAbsent(false)
    try {
      const body = choice
        ? { boutique_id: choice }
        : { nom: newName.trim() || undefined }
      const r = await apiClient.post(`/residences/${kind}/${id}/boutique`, body)
      setState(r.data)
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } }
      if (err.response?.status === 409 && err.response.data?.detail === 'market_not_enabled') {
        setMarketAbsent(true)
      } else if (err.response?.status === 403 && err.response.data?.detail === 'plan_limit_reached') {
        setError('Votre formule ne permet pas de créer davantage de boutiques.')
      } else {
        setError("Le déploiement de la boutique a échoué. Réessayez plus tard.")
      }
    } finally {
      setWorking(false)
    }
  }

  if (loading) return null

  return (
    <div className="bg-white rounded-xl border p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
          <Store size={18} className="text-blue-600" />
        </span>
        <h2 className="font-semibold text-gray-900">Boutique de la résidence</h2>
      </div>

      {state?.linked ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Une boutique Le Comptoir Market est rattachée à cette résidence.
          </p>
          {state.boutique_url && (
            <a href={state.boutique_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-800">
              Ouvrir la boutique <ExternalLink size={14} />
            </a>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Proposez une boutique en ligne aux occupants de cette résidence (commandes,
            retrait sur place). Vous pouvez rattacher plusieurs biens à la même boutique.
          </p>

          {boutiques.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Rattacher à une boutique
              </label>
              <select
                value={choice}
                onChange={(e) => setChoice(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {boutiques.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.nom || 'Boutique de la résidence'}
                  </option>
                ))}
                <option value="">➕ Créer une nouvelle boutique</option>
              </select>
            </div>
          )}

          {(boutiques.length === 0 || choice === '') && (
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Nom de la nouvelle boutique
              </label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Boutique de la résidence"
              />
            </div>
          )}

          {marketAbsent && (
            <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
              Activez d'abord Le Comptoir Market pour votre compte afin de déployer une boutique.
            </p>
          )}
          {error && <p className="text-xs text-red-600">{error}</p>}
          <Button onClick={deploy} disabled={working}>
            {working
              ? 'En cours…'
              : choice
                ? 'Rattacher à cette boutique'
                : 'Créer la boutique'}
          </Button>
        </div>
      )}
    </div>
  )
}
