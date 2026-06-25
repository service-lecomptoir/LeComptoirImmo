import { useEffect, useState } from 'react'
import { Store, ExternalLink, Trash2, Plus, UserPlus, Mail } from 'lucide-react'
import { apiClient } from '@/api/client'
import { Button, Input, Spinner } from '@/components/ui'
import { toast } from '@/store/toast'

interface Gerant {
  gerant_email: string
  exists: boolean
  is_self: boolean
  full_name?: string
}
interface Boutique {
  id: string
  nom: string
  slug?: string | null
  url?: string | null
  gerant_email?: string | null
  gerant_name?: string | null
}
interface Overview {
  market_enabled: boolean
  boutiques: Boutique[]
  gerants: Gerant[]
}

/**
 * Page « Boutique associée » : le gestionnaire rattache autant de gérants Le Comptoir
 * Market qu'il veut (e-mail identique ou différent du sien). Chaque gérant gère ses
 * propres boutiques dans Market ; la page liste ici toutes leurs boutiques en lecture
 * seule. Les locataires du gestionnaire accèdent à toutes ces boutiques.
 */
export default function BoutiqueResidence() {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [newGerant, setNewGerant] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const r = await apiClient.get('/residences/boutiques/overview')
      setData(r.data)
    } catch {
      toast.error('Chargement impossible.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const addGerant = async () => {
    const email = newGerant.trim()
    if (!email || !email.includes('@')) {
      toast.error('Saisissez un e-mail de gérant valide.')
      return
    }
    setWorking(true)
    try {
      const res = await apiClient.post('/residences/boutiques/gerants', { gerant_email: email })
      toast.success(
        res.data?.created
          ? res.data?.email_sent
            ? 'Gérant créé : les identifiants ont été envoyés à cet e-mail.'
            : 'Gérant créé et rattaché.'
          : 'Gérant rattaché.',
      )
      setNewGerant('')
      await load()
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      toast.error(err.response?.data?.detail || 'Rattachement du gérant impossible.')
    } finally {
      setWorking(false)
    }
  }

  const removeGerant = async (email: string) => {
    if (!window.confirm(`Retirer le gérant « ${email} » ? (son compte et ses boutiques ne sont pas supprimés)`)) return
    setWorking(true)
    try {
      await apiClient.delete('/residences/boutiques/gerants', { params: { gerant_email: email } })
      toast.success('Gérant retiré.')
      await load()
    } catch {
      toast.error('Retrait impossible.')
    } finally {
      setWorking(false)
    }
  }

  const openMarket = async (gerantEmail?: string) => {
    setWorking(true)
    try {
      const r = await apiClient.post('/residences/market-login', { gerant_email: gerantEmail || null })
      if (r.data?.url) window.open(r.data.url, '_blank', 'noopener')
      else toast.error('Ouverture impossible.')
    } catch {
      toast.error('Ouverture de Le Comptoir Market impossible. Réessayez plus tard.')
    } finally {
      setWorking(false)
    }
  }

  if (loading) return <div className="p-8 flex justify-center"><Spinner /></div>
  if (!data) return null

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-5">
      <div className="flex items-center gap-2">
        <span className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
          <Store size={20} className="text-blue-600" />
        </span>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-gray-900">Boutique associée</h1>
          <p className="text-sm text-gray-500">
            Rattachez des gérants Le Comptoir Market. Chaque gérant gère ses propres boutiques ;
            vos locataires y ont accès.
          </p>
        </div>
      </div>

      {/* Mes gérants (roster) */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <h2 className="font-semibold text-gray-900">Mes gérants</h2>
        <div className="flex gap-2 flex-wrap">
          <Input
            type="email"
            value={newGerant}
            onChange={(e) => setNewGerant(e.target.value)}
            placeholder="email-du-gerant@exemple.fr"
            className="flex-1 min-w-[220px]"
          />
          <Button onClick={addGerant} disabled={working}>
            <UserPlus size={16} /> Ajouter
          </Button>
        </div>

        {data.gerants.length === 0 ? (
          <p className="text-sm text-gray-500">
            Aucun gérant rattaché. Ajoutez-en un (le vôtre ou un autre) pour proposer une boutique.
          </p>
        ) : (
          <ul className="divide-y">
            {data.gerants.map((g) => (
              <li key={g.gerant_email} className="flex items-center justify-between gap-2 py-2 flex-wrap">
                <div className="min-w-0">
                  <span className="text-sm text-gray-900 break-all">{g.gerant_email}</span>
                  {g.is_self && <span className="text-xs text-gray-400"> (vous-même)</span>}
                  {g.full_name && <span className="text-xs text-gray-500"> — {g.full_name}</span>}
                  {!g.exists && (
                    <span className="ml-1 inline-flex items-center gap-1 text-xs text-amber-600">
                      <Mail size={12} /> identifiants envoyés
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {g.exists && (
                    <Button variant="secondary" onClick={() => openMarket(g.gerant_email)} disabled={working}>
                      <ExternalLink size={14} /> Ouvrir
                    </Button>
                  )}
                  <button
                    onClick={() => removeGerant(g.gerant_email)}
                    className="text-red-500 hover:text-red-700"
                    title="Retirer du roster"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Boutiques (lecture seule) */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-semibold text-gray-900">Boutiques</h2>
          <span className="text-xs text-gray-400 inline-flex items-center gap-1">
            <Plus size={12} /> Les boutiques se créent dans Le Comptoir Market
          </span>
        </div>
        {data.boutiques.length === 0 ? (
          <p className="text-sm text-gray-500">
            Aucune boutique pour le moment. Ouvrez un gérant ci-dessus pour en créer dans Le Comptoir Market.
          </p>
        ) : (
          <ul className="divide-y">
            {data.boutiques.map((b) => (
              <li key={b.id} className="flex items-center justify-between gap-2 py-2 flex-wrap">
                <div className="min-w-0">
                  <span className="font-medium text-gray-900">{b.nom}</span>
                  {b.gerant_name || b.gerant_email ? (
                    <span className="block text-xs text-gray-500 break-all">
                      Gérant : {b.gerant_name || b.gerant_email}
                    </span>
                  ) : null}
                </div>
                {b.url && (
                  <a
                    href={b.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800"
                  >
                    Ouvrir <ExternalLink size={14} />
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
