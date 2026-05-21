import { useState, useEffect } from 'react'
import { Building2, MapPin, Home, TrendingUp } from 'lucide-react'
import { propertiesApi } from '@/api/properties'

export default function ProprietaireBiens() {
  const [properties, setProperties] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    propertiesApi.list({ limit: 100 })
      .then(r => setProperties(r.data.items ?? r.data))
      .catch(() => { })
      .finally(() => setIsLoading(false))
  }, [])

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes biens</h1>
        <p className="text-gray-500 text-sm mt-1">Vue d'ensemble de votre patrimoine en gestion</p>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400 text-sm">
          Chargement…
        </div>
      ) : properties.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400">
          <Building2 size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Aucun bien enregistré</p>
          <p className="text-sm mt-1">Contactez votre gestionnaire pour lier vos biens à votre compte.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {properties.map((p: any) => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
                  <Building2 size={18} className="text-blue-600" />
                </div>
                <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full capitalize">
                  {p.property_type}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-gray-900 mb-1">{p.name}</h3>
              <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
                <MapPin size={11} />
                <span>{p.full_address ?? p.city}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-3 border-t border-gray-100">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 text-gray-400 mb-0.5">
                    <Home size={12} />
                    <span className="text-xs">Logements</span>
                  </div>
                  <p className="text-sm font-bold text-gray-900">
                    {p.occupied_count ?? '—'}/{p.unit_count ?? '—'}
                  </p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 text-gray-400 mb-0.5">
                    <TrendingUp size={12} />
                    <span className="text-xs">Taux occup.</span>
                  </div>
                  <p className="text-sm font-bold text-gray-900">
                    {p.unit_count > 0
                      ? `${Math.round((p.occupied_count / p.unit_count) * 100)} %`
                      : '—'
                    }
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
