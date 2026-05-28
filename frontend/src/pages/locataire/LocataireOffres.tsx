import { useState, useEffect } from 'react'
import { Tag, Euro, Phone, ShoppingBag } from 'lucide-react'
import { offersApi } from '@/api/offers'
import type { Offer } from '@/api/offers'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const CATEGORY_LABELS: Record<string, string> = {
  service:   'Service',
  article:   'Article',
  promotion: 'Promotion',
  autre:     'Autre',
}

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  service:   { bg: 'bg-blue-50',   text: 'text-blue-700' },
  article:   { bg: 'bg-green-50',  text: 'text-green-700' },
  promotion: { bg: 'bg-orange-50', text: 'text-orange-700' },
  autre:     { bg: 'bg-gray-100',  text: 'text-gray-700' },
}

export default function LocataireOffres() {
  const [offers, setOffers] = useState<Offer[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    offersApi.listForTenant()
      .then(r => setOffers(r.data))
      .catch(() => setOffers([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Offres & Services</h1>
        <p className="text-sm text-gray-500 mt-1">Services et offres disponibles pour vous</p>
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-400">Chargement…</div>
      ) : offers.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <ShoppingBag size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium">Aucune offre disponible</p>
          <p className="text-sm text-gray-400 mt-1">Votre gestionnaire n'a pas encore publié d'offres.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {offers.map(o => (
            <div key={o.id} className="bg-white rounded-xl border overflow-hidden hover:shadow-md transition-shadow">
              <div className="flex gap-4 p-5">
                {o.image_url && (
                  <img src={`${API_BASE}${o.image_url}`} alt={o.title}
                    className="w-24 h-24 shrink-0 rounded-lg object-cover" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-2 flex-wrap mb-1">
                    <p className="font-semibold text-gray-900">{o.title}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[o.category]?.bg ?? 'bg-gray-100'} ${CATEGORY_COLORS[o.category]?.text ?? 'text-gray-700'}`}>
                      {CATEGORY_LABELS[o.category] ?? o.category}
                    </span>
                  </div>
                  {o.description && (
                    <p className="text-sm text-gray-600 mt-1">{o.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-3 text-sm">
                    {o.price != null ? (
                      <span className="flex items-center gap-1.5 font-semibold text-gray-900">
                        <Euro size={14} />{Number(o.price).toFixed(2)} €
                      </span>
                    ) : (
                      <span className="text-gray-500 flex items-center gap-1.5">
                        <Tag size={13} /> Prix sur demande
                      </span>
                    )}
                    {o.contact_info && (
                      <span className="flex items-center gap-1.5 text-blue-600">
                        <Phone size={13} />
                        <a href={o.contact_info.includes('@') ? `mailto:${o.contact_info}` : `tel:${o.contact_info}`}
                          className="hover:underline">
                          {o.contact_info}
                        </a>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
