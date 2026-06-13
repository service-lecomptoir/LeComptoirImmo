import { useEffect, useState, useRef } from 'react'
import {
  AlertTriangle, Volume2, ShieldAlert, Trash2, ArrowUpDown, Trees, Hammer, HelpCircle,
  Camera, Clock, Send, X, MapPin,
} from 'lucide-react'
import { signalementsApi, type Signalement, type SignalementCategory, type SignalementUrgency } from '@/api/signalements'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Signalements liés à la résidence / l'immeuble (parties communes, équipements
// collectifs, voisinage). Pas les problèmes du logement privatif.
const CATEGORIES: { key: SignalementCategory; label: string; icon: typeof Volume2 }[] = [
  { key: 'bruit', label: 'Bruit / nuisance sonore', icon: Volume2 },
  { key: 'securite', label: 'Sécurité (accès, interphone, éclairage)', icon: ShieldAlert },
  { key: 'proprete', label: 'Propreté des parties communes', icon: Trash2 },
  { key: 'ascenseur', label: 'Ascenseur', icon: ArrowUpDown },
  { key: 'exterieur', label: 'Espaces extérieurs / parking', icon: Trees },
  { key: 'degradation', label: 'Dégradation / vandalisme', icon: Hammer },
  { key: 'autre', label: 'Autre', icon: HelpCircle },
]

const URGENCIES: { key: SignalementUrgency; label: string; cls: string }[] = [
  { key: 'faible', label: 'Faible', cls: 'border-gray-300 text-gray-700 bg-gray-50' },
  { key: 'moyen', label: 'Moyen', cls: 'border-amber-300 text-amber-800 bg-amber-50' },
  { key: 'urgent', label: 'Urgent', cls: 'border-red-300 text-red-800 bg-red-50' },
]

const URGENCY_BADGE: Record<string, string> = {
  faible: 'bg-gray-100 text-gray-600', moyen: 'bg-amber-100 text-amber-700', urgent: 'bg-red-100 text-red-700',
}
const STATUS_BADGE: Record<string, string> = {
  nouveau: 'bg-blue-100 text-blue-700', en_cours: 'bg-amber-100 text-amber-700',
  resolu: 'bg-green-100 text-green-700', clos: 'bg-gray-100 text-gray-600',
}

// Valeur datetime-local « maintenant » (sans secondes), heure locale.
function nowLocal(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function LocataireSignaler() {
  const [items, setItems] = useState<Signalement[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState<SignalementCategory>('bruit')
  const [urgency, setUrgency] = useState<SignalementUrgency>('moyen')
  const [occurredAt, setOccurredAt] = useState(nowLocal())
  const [description, setDescription] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = async () => {
    setLoading(true)
    try { const { data } = await signalementsApi.mine(); setItems(data) }
    catch { /* silencieux */ }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const reset = () => {
    setCategory('bruit'); setUrgency('moyen'); setOccurredAt(nowLocal())
    setDescription(''); setPhoto(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const submit = async () => {
    if (!description.trim()) { toast.error('Décrivez le problème.'); return }
    setSubmitting(true)
    try {
      const { data } = await signalementsApi.create({
        category, urgency, description: description.trim(),
        // On envoie l'heure « murale » locale telle que saisie (sans conversion UTC) :
        // le créneau nuit (22h-7h) doit être évalué dans l'heure locale du locataire,
        // y compris hors métropole (ex. Guyane UTC-3). Le backend la stocke en naïf.
        occurred_at: occurredAt || null,
      })
      if (photo && data?.id) {
        try { await signalementsApi.uploadPhoto(data.id, photo) }
        catch (e: any) { toast.error(getErrorMessage(e, "La photo n'a pas pu être envoyée")) }
      }
      reset()
      await load()
    } catch (e: any) {
      toast.error(getErrorMessage(e, "Le signalement n'a pas pu être envoyé"))
    } finally { setSubmitting(false) }
  }

  return (
    <div className="max-w-3xl p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <AlertTriangle size={22} className="text-amber-500" /> Vie de la résidence
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Signalez un problème lié à la résidence ou à l'immeuble : parties communes, ascenseur,
          sécurité des accès, propreté, espaces extérieurs, nuisances de voisinage… Votre gestionnaire est alerté immédiatement.
          Pour un souci dans votre logement, passez par une demande d'intervention.
        </p>
      </div>

      {/* Formulaire */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-2">Catégorie</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {CATEGORIES.map(c => {
              const Icon = c.icon
              const active = category === c.key
              return (
                <button key={c.key} type="button" onClick={() => setCategory(c.key)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm text-left transition-colors ${active ? 'border-blue-500 bg-blue-50 text-blue-900' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                  <Icon size={16} className={active ? 'text-blue-600' : 'text-gray-400'} />
                  <span className="leading-tight">{c.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">Niveau d'urgence</label>
            <div className="flex gap-2">
              {URGENCIES.map(u => (
                <button key={u.key} type="button" onClick={() => setUrgency(u.key)}
                  className={`flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${urgency === u.key ? u.cls + ' ring-2 ring-offset-1 ring-blue-200' : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
                  {u.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2 flex items-center gap-1"><Clock size={13} /> Date et heure</label>
            <input type="datetime-local" value={occurredAt} onChange={e => setOccurredAt(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3}
            placeholder="Ex. Ascenseur en panne depuis ce matin / hall non nettoyé / porte d'entrée qui ne ferme plus."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Photo (optionnel)</label>
          {photo ? (
            <div className="flex items-center gap-2 text-sm text-gray-700">
              <Camera size={15} className="text-gray-400" /> {photo.name}
              <button type="button" onClick={() => { setPhoto(null); if (fileRef.current) fileRef.current.value = '' }}
                className="text-gray-400 hover:text-red-600"><X size={15} /></button>
            </div>
          ) : (
            <button type="button" onClick={() => fileRef.current?.click()}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600">
              <Camera size={15} /> Ajouter une photo
            </button>
          )}
          <input ref={fileRef} type="file" accept="image/*" className="hidden"
            onChange={e => setPhoto(e.target.files?.[0] || null)} />
        </div>

        <div className="flex justify-end">
          <button onClick={submit} disabled={submitting}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
            <Send size={15} /> {submitting ? 'Envoi…' : 'Envoyer le signalement'}
          </button>
        </div>
      </div>

      {/* Mes signalements */}
      <h2 className="text-sm font-semibold text-gray-900 mt-8 mb-3">Mes signalements</h2>
      {loading ? (
        <p className="text-sm text-gray-400">Chargement…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-400">Aucun signalement pour le moment.</p>
      ) : (
        <div className="space-y-3">
          {items.map(s => (
            <div key={s.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900">{s.category_label}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${URGENCY_BADGE[s.urgency]}`}>{s.urgency_label}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[s.status]}`}>{s.status_label}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 whitespace-pre-line">{s.description}</p>
                  {s.property_name && (
                    <p className="text-xs text-gray-400 mt-1 flex items-center gap-1"><MapPin size={11} /> {s.property_name}</p>
                  )}
                  {s.resolution_note && (
                    <p className="text-xs text-green-700 mt-1.5 bg-green-50 border border-green-100 rounded px-2 py-1">Réponse du gestionnaire : {s.resolution_note}</p>
                  )}
                </div>
                {s.photo_url && (
                  <a href={`${API_BASE}${s.photo_url}`} target="_blank" rel="noreferrer" className="shrink-0">
                    <img src={`${API_BASE}${s.photo_url}`} alt="photo" className="w-16 h-16 object-cover rounded-lg border border-gray-200" />
                  </a>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-2">
                {s.occurred_at ? `Survenu le ${format(new Date(s.occurred_at), 'd MMM yyyy à HH:mm', { locale: fr })}` : ''}
                {' · '}signalé le {format(new Date(s.created_at), 'd MMM yyyy', { locale: fr })}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
