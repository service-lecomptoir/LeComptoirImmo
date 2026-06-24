import { useState, useEffect } from 'react'
import { Button } from '@/components/ui'
import { formatPhoneDisplay } from '@/utils/format'
import { apiClient } from '@/api/client'
import AddressAutocomplete from '@/components/common/AddressAutocomplete'
import SiretInput from '@/components/common/SiretInput'
import {
  Phone, Mail, MapPin, Star, Plus, Search,
  Trash2, Edit2, Building2, Wrench, Zap, Paintbrush,
  Lock, Flame, Leaf, Sparkles, Scale, Shield, Landmark, Users, Filter
} from 'lucide-react'

const CATEGORIES = [
  { value: '', label: 'Toutes catégories', icon: Filter },
  { value: 'plombier', label: 'Plombier', icon: Wrench },
  { value: 'electricien', label: 'Électricien', icon: Zap },
  { value: 'menuisier', label: 'Menuisier', icon: Building2 },
  { value: 'peintre', label: 'Peintre', icon: Paintbrush },
  { value: 'serrurier', label: 'Serrurier', icon: Lock },
  { value: 'chauffagiste', label: 'Chauffagiste', icon: Flame },
  { value: 'jardinier', label: 'Jardinier', icon: Leaf },
  { value: 'nettoyage', label: 'Nettoyage', icon: Sparkles },
  { value: 'architecte', label: 'Architecte', icon: Building2 },
  { value: 'notaire', label: 'Notaire', icon: Scale },
  { value: 'avocat', label: 'Avocat', icon: Scale },
  { value: 'assurance', label: 'Assurance', icon: Shield },
  { value: 'banque', label: 'Banque', icon: Landmark },
  { value: 'autre', label: 'Autre', icon: Users },
]

const CATEGORY_COLORS: Record<string, string> = {
  plombier: 'bg-blue-100 text-blue-700',
  electricien: 'bg-yellow-100 text-yellow-700',
  menuisier: 'bg-amber-100 text-amber-700',
  peintre: 'bg-pink-100 text-pink-700',
  serrurier: 'bg-gray-100 text-gray-700',
  chauffagiste: 'bg-orange-100 text-orange-700',
  jardinier: 'bg-green-100 text-green-700',
  nettoyage: 'bg-cyan-100 text-cyan-700',
  architecte: 'bg-indigo-100 text-indigo-700',
  notaire: 'bg-purple-100 text-purple-700',
  avocat: 'bg-purple-100 text-purple-700',
  assurance: 'bg-teal-100 text-teal-700',
  banque: 'bg-emerald-100 text-emerald-700',
  autre: 'bg-gray-100 text-gray-600',
}

interface Contact {
  id: string
  first_name?: string
  last_name: string
  company_name?: string
  display_name: string
  full_name: string
  category: string
  email?: string
  phone?: string
  phone2?: string
  address?: string
  zip_code?: string
  city?: string
  siret?: string
  website?: string
  notes?: string
  is_favorite: boolean
}

interface ContactModalProps {
  contact?: Contact | null
  onClose: () => void
  onSaved: () => void
}

function ContactModal({ contact, onClose, onSaved }: ContactModalProps) {
  const [form, setForm] = useState({
    first_name: contact?.first_name || '',
    last_name: contact?.last_name || '',
    company_name: contact?.company_name || '',
    category: contact?.category || 'autre',
    email: contact?.email || '',
    phone: contact?.phone || '',
    phone2: contact?.phone2 || '',
    address: contact?.address || '',
    zip_code: contact?.zip_code || '',
    city: contact?.city || '',
    siret: contact?.siret || '',
    website: contact?.website || '',
    notes: contact?.notes || '',
    is_favorite: contact?.is_favorite || false,
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (contact?.id) {
        await apiClient.patch(`/contacts/${contact.id}`, form)
      } else {
        await apiClient.post('/contacts', form)
      }
      onSaved()
      onClose()
    } catch {
      // Le message d'erreur est affiché par l'intercepteur axios (toast).
      // On ne ferme pas la modale : l'utilisateur peut corriger et réessayer.
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">
            {contact ? 'Modifier le contact' : 'Nouveau contact'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prénom</label>
              <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.first_name}
                onChange={e => setForm({ ...form, first_name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nom *</label>
              <input required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.last_name}
                onChange={e => setForm({ ...form, last_name: e.target.value })} />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Société</label>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.company_name}
              onChange={e => setForm({ ...form, company_name: e.target.value })} />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Catégorie</label>
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.category}
              onChange={e => setForm({ ...form, category: e.target.value })}>
              {CATEGORIES.filter(c => c.value).map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Téléphone</label>
              <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.phone}
                onChange={e => setForm({ ...form, phone: e.target.value })} />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Adresse</label>
            <AddressAutocomplete
              value={form.address}
              onChange={v => setForm({ ...form, address: v })}
              onSelect={({ street, postcode, city }) => setForm(f => ({
                ...f,
                address: street,
                zip_code: postcode || f.zip_code,
                city: city || f.city,
              }))}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Code postal</label>
              <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.zip_code}
                onChange={e => setForm({ ...form, zip_code: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Ville</label>
              <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.city}
                onChange={e => setForm({ ...form, city: e.target.value })} />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">SIRET</label>
              <SiretInput className="w-full border rounded-lg px-3 py-2 text-sm" value={form.siret}
                onChange={v => setForm({ ...form, siret: v })}
                onResolved={name => setForm(f => (f.company_name.trim() ? f : { ...f, company_name: name }))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Site web</label>
              <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.website}
                onChange={e => setForm({ ...form, website: e.target.value })} />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea rows={3} className="w-full border rounded-lg px-3 py-2 text-sm" value={form.notes}
              onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>

          <div className="flex items-center gap-2">
            <input type="checkbox" id="fav" checked={form.is_favorite}
              onChange={e => setForm({ ...form, is_favorite: e.target.checked })} />
            <label htmlFor="fav" className="text-sm text-gray-700">Marquer comme favori</label>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg text-sm text-gray-700 hover:bg-gray-50">
              Annuler
            </button>
            <Button type="submit" disabled={saving} className="flex-1">
              {saving ? 'Sauvegarde...' : 'Enregistrer'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function ContactList() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editContact, setEditContact] = useState<Contact | null>(null)

  const load = () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (category) params.category = category
    if (favoritesOnly) params.favorites_only = 'true'

    apiClient.get('/contacts', { params })
      .then(r => setContacts(r.data))
      .catch(() => setContacts([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [search, category, favoritesOnly])

  const toggleFavorite = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await apiClient.post(`/contacts/${id}/toggle-favorite`)
      load()
    } catch {
      // erreur affichée par l'intercepteur (toast)
    }
  }

  const deleteContact = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Supprimer ce contact ?')) return
    try {
      await apiClient.delete(`/contacts/${id}`)
      load()
    } catch {
      // erreur affichée par l'intercepteur (toast)
    }
  }

  const catLabel = (val: string) => CATEGORIES.find(c => c.value === val)?.label || val

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Carnet d'adresses</h1>
          <p className="text-sm text-gray-500 mt-1">Prestataires, notaires, assureurs…</p>
        </div>
        <Button
          onClick={() => { setEditContact(null); setShowModal(true) }}
          leftIcon={<Plus size={16} />}
        >
          Nouveau contact
        </Button>
      </div>

      {/* Filtres */}
      <div className="bg-white rounded-xl border p-4 mb-6 flex flex-wrap gap-4">
        <div className="flex-1 min-w-48 relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            placeholder="Rechercher..."
            className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={category}
          onChange={e => setCategory(e.target.value)}
        >
          {CATEGORIES.map(c => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <button
          onClick={() => setFavoritesOnly(!favoritesOnly)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition-colors ${
            favoritesOnly ? 'bg-yellow-50 border-yellow-300 text-yellow-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
          }`}
        >
          <Star size={14} className={favoritesOnly ? 'fill-yellow-500 text-yellow-500' : ''} />
          Favoris
        </button>
      </div>

      {/* Stats */}
      <div className="text-sm text-gray-500 mb-4">{contacts.length} contact{contacts.length > 1 ? 's' : ''}</div>

      {/* Grille contacts */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Chargement…</div>
      ) : contacts.length === 0 ? (
        <div className="text-center py-12">
          <Users size={48} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">Aucun contact trouvé</p>
          <button
            onClick={() => { setEditContact(null); setShowModal(true) }}
            className="mt-4 text-blue-600 text-sm hover:underline"
          >
            Ajouter un premier contact
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contacts.map(c => (
            <div
              key={c.id}
              className="bg-white rounded-xl border p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => { setEditContact(c); setShowModal(true) }}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900 text-sm">{c.display_name}</p>
                    {c.company_name && c.full_name !== c.display_name && (
                      <span className="text-xs text-gray-400">{c.full_name}</span>
                    )}
                  </div>
                  <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[c.category] || 'bg-gray-100 text-gray-600'}`}>
                    {catLabel(c.category)}
                  </span>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <button onClick={e => toggleFavorite(c.id, e)}
                    className="p-1 hover:text-yellow-500 transition-colors">
                    <Star size={16} className={c.is_favorite ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'} />
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                {c.phone && (
                  <div className="flex items-center gap-2 text-xs text-gray-600">
                    <Phone size={12} className="text-gray-400 shrink-0" />
                    <span>{formatPhoneDisplay(c.phone)}</span>
                  </div>
                )}
                {c.email && (
                  <div className="flex items-center gap-2 text-xs text-gray-600">
                    <Mail size={12} className="text-gray-400 shrink-0" />
                    <span className="truncate">{c.email}</span>
                  </div>
                )}
                {c.city && (
                  <div className="flex items-center gap-2 text-xs text-gray-600">
                    <MapPin size={12} className="text-gray-400 shrink-0" />
                    <span>{[c.zip_code, c.city].filter(Boolean).join(' ')}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-2 mt-3 pt-3 border-t">
                <button onClick={e => { e.stopPropagation(); setEditContact(c); setShowModal(true) }}
                  className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-lg">
                  <Edit2 size={14} />
                </button>
                <button onClick={e => deleteContact(c.id, e)}
                  className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <ContactModal
          contact={editContact}
          onClose={() => setShowModal(false)}
          onSaved={load}
        />
      )}
    </div>
  )
}
