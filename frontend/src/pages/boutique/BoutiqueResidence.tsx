import { useEffect, useState } from 'react'
import { Store, ExternalLink, Trash2, Pencil, Plus, Check, X } from 'lucide-react'
import { apiClient } from '@/api/client'
import { Button, Input, Spinner } from '@/components/ui'
import { toast } from '@/store/toast'

interface ResidenceRef {
  kind: 'property' | 'copropriete'
  id: string
  name: string
}
interface Boutique {
  id: string
  nom: string
  slug?: string | null
  url?: string | null
  residences: ResidenceRef[]
}
interface ManagerResidence extends ResidenceRef {
  boutique_id?: string | null
}
interface Plan {
  id: string
  name: string
  monthly_price?: number | null
  property_limit?: number | null
  description?: string | null
}
interface Overview {
  market_enabled: boolean
  boutiques: Boutique[]
  residences: ManagerResidence[]
  plans: Plan[]
}

function euros(v?: number | null): string {
  if (v === null || v === undefined) return ''
  return v.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
}

/**
 * Page « Boutique de la résidence » : gérer (créer / renommer / supprimer) les
 * boutiques Le Comptoir Market d'une résidence et rattacher des biens. Si le
 * compte n'a pas encore de gérant Market, propose de le créer (choix du plan).
 */
export default function BoutiqueResidence() {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [newName, setNewName] = useState('')
  const [editId, setEditId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [manageId, setManageId] = useState<string | null>(null)
  const [planId, setPlanId] = useState<string>('')

  const load = async () => {
    setLoading(true)
    try {
      const r = await apiClient.get('/residences/boutiques/overview')
      setData(r.data)
      if (r.data.plans?.length && !planId) setPlanId(r.data.plans[0].id)
    } catch {
      toast.error('Chargement impossible.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const activate = async () => {
    setWorking(true)
    try {
      const res = await apiClient.post('/residences/activate-market', { plan_id: planId || null })
      toast.success(
        res.data?.email_sent
          ? 'Compte boutique créé : vos identifiants vous ont été envoyés par e-mail.'
          : 'Compte boutique activé.',
      )
      await load()
    } catch {
      toast.error("L'activation a échoué. Réessayez plus tard.")
    } finally {
      setWorking(false)
    }
  }

  const create = async () => {
    setWorking(true)
    try {
      await apiClient.post('/residences/boutiques', { nom: newName.trim() || undefined })
      setNewName('')
      toast.success('Boutique créée.')
      await load()
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } }
      if (err.response?.status === 403 && err.response.data?.detail === 'plan_limit_reached') {
        toast.error('Votre formule ne permet pas de créer davantage de boutiques.')
      } else {
        toast.error('Création impossible.')
      }
    } finally {
      setWorking(false)
    }
  }

  const rename = async (id: string) => {
    if (!editName.trim()) return
    setWorking(true)
    try {
      await apiClient.patch(`/residences/boutiques/${id}`, { nom: editName.trim() })
      setEditId(null)
      toast.success('Boutique renommée.')
      await load()
    } catch {
      toast.error('Renommage impossible.')
    } finally {
      setWorking(false)
    }
  }

  const remove = async (b: Boutique) => {
    if (!window.confirm(`Supprimer définitivement la boutique « ${b.nom} » ?`)) return
    setWorking(true)
    try {
      await apiClient.delete(`/residences/boutiques/${b.id}`)
      toast.success('Boutique supprimée.')
      await load()
    } catch {
      toast.error('Suppression impossible.')
    } finally {
      setWorking(false)
    }
  }

  const toggleResidence = async (b: Boutique, res: ManagerResidence, attach: boolean) => {
    if (!data) return
    // Construit la nouvelle liste des biens rattachés à CETTE boutique.
    const current = data.residences.filter((r) => r.boutique_id === b.id)
    let items = current.map((r) => ({ kind: r.kind, id: r.id }))
    if (attach) items = [...items, { kind: res.kind, id: res.id }]
    else items = items.filter((r) => !(r.kind === res.kind && r.id === res.id))
    setWorking(true)
    try {
      await apiClient.put(`/residences/boutiques/${b.id}/residences`, { items })
      await load()
    } catch {
      toast.error('Mise à jour des biens impossible.')
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
        <div>
          <h1 className="text-xl font-bold text-gray-900">Boutique de la résidence</h1>
          <p className="text-sm text-gray-500">
            Proposez une boutique en ligne aux occupants de vos résidences (Le Comptoir Market).
          </p>
        </div>
      </div>

      {!data.market_enabled ? (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <p className="text-sm text-gray-700">
            Vous n'avez pas encore de boutique Le Comptoir Market. Créez votre compte
            directement : vos informations sont reprises de votre compte, choisissez simplement
            une formule.
          </p>
          {data.plans.length > 0 && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Formule</label>
              <div className="grid sm:grid-cols-2 gap-2">
                {data.plans.map((p) => (
                  <label
                    key={p.id}
                    className={`block border rounded-lg p-3 cursor-pointer ${planId === p.id ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-300'}`}
                  >
                    <input
                      type="radio"
                      name="plan"
                      value={p.id}
                      checked={planId === p.id}
                      onChange={() => setPlanId(p.id)}
                      className="mr-2"
                    />
                    <span className="font-semibold">{p.name}</span>
                    {p.monthly_price != null && (
                      <span className="block text-sm">{euros(p.monthly_price)} € / mois</span>
                    )}
                    <span className="block text-xs text-gray-500">
                      {p.property_limit
                        ? `Jusqu'à ${p.property_limit} boutique${p.property_limit > 1 ? 's' : ''}`
                        : 'Boutiques illimitées'}
                    </span>
                    {p.description && (
                      <span className="block text-xs text-gray-500">{p.description}</span>
                    )}
                  </label>
                ))}
              </div>
            </div>
          )}
          <Button onClick={activate} disabled={working}>
            {working ? 'Création…' : 'Créer mon compte boutique'}
          </Button>
        </div>
      ) : (
        <>
          {/* Ajouter une boutique */}
          <div className="bg-white rounded-xl border p-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nouvelle boutique
            </label>
            <div className="flex gap-2">
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Nom de la boutique"
              />
              <Button onClick={create} disabled={working}>
                <Plus size={16} /> Ajouter
              </Button>
            </div>
          </div>

          {data.boutiques.length === 0 && (
            <p className="text-sm text-gray-500">Aucune boutique pour le moment.</p>
          )}

          {data.boutiques.map((b) => (
            <div key={b.id} className="bg-white rounded-xl border p-4 space-y-3">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                {editId === b.id ? (
                  <div className="flex gap-2 items-center flex-1">
                    <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
                    <Button onClick={() => rename(b.id)} disabled={working}>
                      <Check size={16} />
                    </Button>
                    <Button variant="secondary" onClick={() => setEditId(null)}>
                      <X size={16} />
                    </Button>
                  </div>
                ) : (
                  <h2 className="font-semibold text-gray-900">{b.nom}</h2>
                )}
                <div className="flex items-center gap-2">
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
                  {editId !== b.id && (
                    <button
                      onClick={() => { setEditId(b.id); setEditName(b.nom) }}
                      className="text-gray-500 hover:text-gray-800"
                      title="Renommer"
                    >
                      <Pencil size={16} />
                    </button>
                  )}
                  <button
                    onClick={() => remove(b)}
                    className="text-red-500 hover:text-red-700"
                    title="Supprimer"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              <div className="text-sm text-gray-600">
                {b.residences.length === 0 ? (
                  <span className="text-gray-400">Aucun bien rattaché.</span>
                ) : (
                  <span>
                    Biens rattachés : {b.residences.map((r) => r.name).join(', ')}
                  </span>
                )}
              </div>

              <button
                onClick={() => setManageId(manageId === b.id ? null : b.id)}
                className="text-sm font-medium text-blue-600 hover:text-blue-800"
              >
                {manageId === b.id ? 'Masquer' : 'Gérer les biens rattachés'}
              </button>

              {manageId === b.id && (
                <div className="border-t pt-3 space-y-1.5">
                  {data.residences.length === 0 && (
                    <p className="text-sm text-gray-400">Aucun bien disponible.</p>
                  )}
                  {data.residences.map((r) => {
                    const attachedHere = r.boutique_id === b.id
                    const attachedElsewhere = !!r.boutique_id && r.boutique_id !== b.id
                    return (
                      <label key={`${r.kind}:${r.id}`} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={attachedHere}
                          disabled={working}
                          onChange={(e) => toggleResidence(b, r, e.target.checked)}
                        />
                        <span>{r.name}</span>
                        {attachedElsewhere && (
                          <span className="text-xs text-amber-600">(rattaché à une autre boutique)</span>
                        )}
                      </label>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  )
}
