import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient } from '@/api/client'
import { MapPin, Home } from 'lucide-react'

interface PublicListing {
  title?: string | null
  description?: string | null
  price?: number | null
  photos: string[]
  contact_name?: string | null
  property: {
    city?: string; zip_code?: string; property_type?: string; typology?: string
    area_sqm?: number | null; floor?: number | null; bathrooms?: number | null
    energy_class?: string | null; heating_type?: string | null; furnished?: boolean
    features?: Record<string, boolean>
  }
}

const FEATURE_LABELS: Record<string, string> = {
  elevator: 'Ascenseur', balcony: 'Balcon', terrace: 'Terrasse', garden: 'Jardin',
  parking: 'Parking', cellar: 'Cave', fiber: 'Fibre', air_conditioning: 'Climatisation',
}

const media = (p: string) => (/^https?:\/\//.test(p) ? p : `${import.meta.env.VITE_API_URL || ''}${p}`)

export default function AnnoncePublic() {
  const { token } = useParams<{ token: string }>()
  const [listing, setListing] = useState<PublicListing | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [active, setActive] = useState(0)

  // ── Candidature ──
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '', employment: '', monthly_income: '', has_guarantor: false, message: '',
  })
  const [applyState, setApplyState] = useState<'idle' | 'sending' | 'done' | 'dup' | 'error'>('idle')

  const apply = async (e: React.FormEvent) => {
    e.preventDefault()
    const fullName = `${form.first_name.trim()} ${form.last_name.trim()}`.trim()
    if (!token || !fullName || !form.email.trim()) return
    setApplyState('sending')
    try {
      const r = await apiClient.post<{ status: string }>(`/public/listings/${token}/apply`, {
        full_name: fullName,
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        employment: form.employment.trim() || null,
        monthly_income: form.monthly_income.trim() ? Number(form.monthly_income) : null,
        has_guarantor: form.has_guarantor,
        message: form.message.trim() || null,
      })
      setApplyState(r.data.status === 'already_applied' ? 'dup' : 'done')
    } catch {
      setApplyState('error')
    }
  }

  useEffect(() => {
    if (!token) return
    apiClient.get<PublicListing>(`/public/listings/${token}`)
      .then(r => setListing(r.data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Chargement…</div>
  }
  if (notFound || !listing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center px-6">
        <Home size={40} className="text-gray-300 mb-3" />
        <h1 className="text-xl font-bold text-gray-900">Annonce introuvable</h1>
        <p className="text-gray-500 mt-1 text-sm">Cette annonce n'est plus disponible.</p>
      </div>
    )
  }

  const p = listing.property
  const url = typeof window !== 'undefined' ? window.location.href : ''
  const title = listing.title || 'Annonce'
  const chips = [
    p.typology, p.area_sqm ? `${p.area_sqm} m²` : null,
    p.floor != null ? `Étage ${p.floor}` : null,
    p.bathrooms != null ? `${p.bathrooms} sdb` : null,
    p.furnished ? 'Meublé' : null,
    p.energy_class ? `DPE ${p.energy_class}` : null,
    p.heating_type || null,
  ].filter(Boolean) as string[]
  const feats = Object.entries(p.features || {}).filter(([, v]) => v).map(([k]) => FEATURE_LABELS[k] || k)

  const share = (kind: string) => {
    const text = encodeURIComponent(title)
    const u = encodeURIComponent(url)
    const links: Record<string, string> = {
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${u}`,
      whatsapp: `https://wa.me/?text=${text}%20${u}`,
      x: `https://twitter.com/intent/tweet?text=${text}&url=${u}`,
      email: `mailto:?subject=${text}&body=${u}`,
    }
    if (kind === 'copy') { navigator.clipboard?.writeText(url); return }
    window.open(links[kind], '_blank', 'noopener')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold" style={{ background: '#0D2F5C' }}>LC</div>
          <span className="font-semibold text-gray-900 text-sm">Le Comptoir Immo</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Galerie */}
        {listing.photos.length > 0 ? (
          <div className="mb-5">
            <div className="rounded-2xl overflow-hidden bg-gray-200 aspect-[16/10]">
              <img src={media(listing.photos[active])} alt={title} className="w-full h-full object-cover" />
            </div>
            {listing.photos.length > 1 && (
              <div className="flex gap-2 mt-2 overflow-x-auto">
                {listing.photos.map((ph, i) => (
                  <button key={i} onClick={() => setActive(i)}
                    className={`h-16 w-24 rounded-lg overflow-hidden shrink-0 border-2 ${i === active ? 'border-blue-600' : 'border-transparent'}`}>
                    <img src={media(ph)} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="mb-5 rounded-2xl bg-gray-100 aspect-[16/10] flex items-center justify-center text-gray-300">
            <Home size={48} />
          </div>
        )}

        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
              {(p.city || p.zip_code) && (
                <p className="flex items-center gap-1.5 text-gray-500 mt-1 text-sm">
                  <MapPin size={14} /> {[p.zip_code, p.city].filter(Boolean).join(' ')}
                </p>
              )}
            </div>
            {listing.price != null && (
              <div className="text-right">
                <p className="text-2xl font-bold" style={{ color: '#0E9F8E' }}>
                  {listing.price.toLocaleString('fr-FR')} €
                </p>
                <p className="text-xs text-gray-400">par mois (CC)</p>
              </div>
            )}
          </div>

          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {chips.map((c, i) => (
                <span key={i} className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">{c}</span>
              ))}
            </div>
          )}

          {listing.description && (
            <p className="text-sm text-gray-700 whitespace-pre-wrap mt-5 leading-relaxed">{listing.description}</p>
          )}

          {feats.length > 0 && (
            <div className="mt-5">
              <h2 className="text-sm font-semibold text-gray-900 mb-2">Équipements</h2>
              <div className="flex flex-wrap gap-2">
                {feats.map((f, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700">{f}</span>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 pt-5 border-t border-gray-100 flex items-center justify-between gap-4 flex-wrap">
            <div className="text-sm text-gray-500">
              {listing.contact_name && <>Contact : <span className="font-medium text-gray-800">{listing.contact_name}</span></>}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => share('copy')} className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700">Copier le lien</button>
              <button onClick={() => share('whatsapp')} className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-green-100 hover:bg-green-200 text-green-700">WhatsApp</button>
              <button onClick={() => share('facebook')} className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-100 hover:bg-blue-200 text-blue-700">Facebook</button>
              <button onClick={() => share('email')} className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700">E-mail</button>
            </div>
          </div>
        </div>

        {/* ── Candidater ── */}
        <div id="candidater" className="bg-white rounded-2xl border border-gray-200 p-6 mt-6">
          <h2 className="text-lg font-bold text-gray-900">Candidater à cette annonce</h2>
          <p className="text-sm text-gray-500 mt-1">Déposez votre dossier : le gestionnaire vous recontactera.</p>

          {applyState === 'done' ? (
            <div className="mt-4 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800">
              ✅ Candidature envoyée. Le gestionnaire reviendra vers vous rapidement.
            </div>
          ) : applyState === 'dup' ? (
            <div className="mt-4 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              Vous avez déjà candidaté à cette annonce avec cet e-mail.
            </div>
          ) : (
            <form onSubmit={apply} className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input required placeholder="Prénom *" value={form.first_name}
                onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input required placeholder="Nom *" value={form.last_name}
                onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input required type="email" placeholder="E-mail *" value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Téléphone" value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Situation professionnelle (CDI, étudiant…)" value={form.employment}
                onChange={e => setForm(f => ({ ...f, employment: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <input type="number" min="0" placeholder="Revenus mensuels nets (€)" value={form.monthly_income}
                onChange={e => setForm(f => ({ ...f, monthly_income: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <label className="flex items-center gap-2 text-sm text-gray-700 px-1">
                <input type="checkbox" checked={form.has_guarantor}
                  onChange={e => setForm(f => ({ ...f, has_guarantor: e.target.checked }))} />
                J'ai un garant
              </label>
              <textarea placeholder="Message (facultatif)" value={form.message} rows={3}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none sm:col-span-2" />
              {applyState === 'error' && (
                <p className="text-sm text-red-600 sm:col-span-2">Échec de l'envoi — vérifiez vos informations puis réessayez.</p>
              )}
              <div className="sm:col-span-2 flex justify-end">
                <button type="submit" disabled={applyState === 'sending'}
                  className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
                  style={{ background: '#0D2F5C' }}>
                  {applyState === 'sending' ? 'Envoi…' : 'Envoyer ma candidature'}
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">Annonce diffusée via Le Comptoir Immo</p>
      </main>
    </div>
  )
}
