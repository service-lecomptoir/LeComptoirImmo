import { useEffect, useState } from 'react'
import { Store, ExternalLink } from 'lucide-react'
import { apiClient } from '@/api/client'
import { Button } from '@/components/ui'

interface Props {
  kind: 'property' | 'copropriete'
  id: string
}

interface LinkState {
  linked: boolean
  boutique_url?: string | null
}

/**
 * Pont Le Comptoir Market : carte « Boutique de la résidence » sur le détail d'un
 * bien ou d'une copropriété. Permet au gestionnaire de déployer/ouvrir la boutique
 * de la résidence. Si le compte n'a pas Le Comptoir Market activé, affiche une CTA.
 */
export default function ResidenceBoutiqueCard({ kind, id }: Props) {
  const [state, setState] = useState<LinkState | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [marketAbsent, setMarketAbsent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    apiClient
      .get(`/residences/${kind}/${id}/boutique`)
      .then((r) => { if (alive) setState(r.data) })
      .catch(() => { if (alive) setState({ linked: false }) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [kind, id])

  const deploy = async () => {
    setWorking(true)
    setError(null)
    setMarketAbsent(false)
    try {
      const r = await apiClient.post(`/residences/${kind}/${id}/boutique`)
      setState(r.data)
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } }
      if (err.response?.status === 409 && err.response.data?.detail === 'market_not_enabled') {
        setMarketAbsent(true)
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
            retrait sur place). La boutique est gérée dans Le Comptoir Market.
          </p>
          {marketAbsent && (
            <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
              Activez d'abord Le Comptoir Market pour votre compte afin de déployer une boutique.
            </p>
          )}
          {error && <p className="text-xs text-red-600">{error}</p>}
          <Button onClick={deploy} disabled={working}>
            {working ? 'Déploiement…' : 'Déployer la boutique'}
          </Button>
        </div>
      )}
    </div>
  )
}
