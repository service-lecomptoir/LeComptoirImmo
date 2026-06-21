import { useState, useEffect } from 'react'
import { Building2, MapPin, ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react'
import { propertiesApi } from '@/api/properties'
import { apiClient } from '@/api/client'
import type { PropertyListItem } from '@/types/property'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' €'

const MONTH_LABELS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

interface MonthBreakdown {
  month: number
  expected: number
  received: number
}

interface PropertyPerf {
  property_id: string
  property_name: string
  monthly_expected: number
  ytd_theoretical: number
  ytd_received: number
  collection_rate: number
  months_elapsed: number
  active_months: number
  monthly_breakdown: MonthBreakdown[]
}

interface PerfData {
  year: number
  months_elapsed: number
  total_theoretical: number
  total_received: number
  global_collection_rate: number
  properties: PropertyPerf[]
}

// ── Barre de recouvrement ─────────────────────────────────────────────────────

function CollectionBar({ rate }: { rate: number }) {
  const filled = Math.min(rate, 100)
  const barColor = rate >= 90 ? 'bg-green-500' : rate >= 65 ? 'bg-yellow-400' : 'bg-red-400'
  const textColor = rate >= 90 ? 'text-green-700' : rate >= 65 ? 'text-yellow-700' : 'text-red-600'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${filled}%` }}
        />
      </div>
      <span className={`text-xs font-bold w-12 text-right tabular-nums ${textColor}`}>
        {rate} %
      </span>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function ProprietaireBiens() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [properties, setProperties] = useState<PropertyListItem[]>([])
  const [perfData, setPerfData] = useState<PerfData | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    setPerfData(null)

    Promise.allSettled([
      propertiesApi.list({ limit: 100 }),
      apiClient.get(`/proprietaire-performance/${year}`),
    ]).then(([propsRes, perfRes]) => {
      if (propsRes.status === 'fulfilled') {
        const items = (propsRes.value.data as any).items ?? propsRes.value.data
        setProperties(items)
      }
      if (perfRes.status === 'fulfilled') {
        setPerfData(perfRes.value.data)
      }
    }).finally(() => setIsLoading(false))
  }, [year])

  const toggleExpand = (id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
  }

  // Merge: properties list (meta) + perf data
  const perfByPropId = new Map(
    perfData?.properties.map(p => [p.property_id, p]) ?? []
  )
  const merged = properties.map(prop => ({
    ...prop,
    perf: perfByPropId.get(prop.id) ?? null,
  }))

  return (
    <div className="p-4 sm:p-6">
      {/* ── En-tête ── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Performance de mes biens</h1>
          <p className="text-gray-500 text-sm mt-1">
            Loyer théorique vs loyer encaissé : accumulation sur l'année
          </p>
        </div>
        <select
          value={year}
          onChange={e => setYear(Number(e.target.value))}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {[currentYear, currentYear - 1, currentYear - 2].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* ── Résumé global ── */}
      {!isLoading && perfData && perfData.total_theoretical > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
              Théorique {year}
            </p>
            <p className="text-2xl font-bold text-gray-800">{fmtEuro(perfData.total_theoretical)}</p>
            <p className="text-xs text-gray-400 mt-1">
              Loyers dus depuis janvier {year} (prorata des contrats)
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
              Encaissé {year}
            </p>
            <p className="text-2xl font-bold text-green-700">{fmtEuro(perfData.total_received)}</p>
            <p className="text-xs text-gray-400 mt-1">
              {perfData.total_theoretical > perfData.total_received
                ? `${fmtEuro(perfData.total_theoretical - perfData.total_received)} non encaissé`
                : '✓ Intégralité perçue'}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Taux de recouvrement
            </p>
            <CollectionBar rate={perfData.global_collection_rate} />
            <p className="text-xs text-gray-400 mt-2">Ensemble du patrimoine</p>
          </div>
        </div>
      )}

      {/* ── Contenu ── */}
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
        <div className="space-y-4">
          {merged.map(prop => {
            const perf = prop.perf
            const isOpen = !!expanded[prop.id]

            return (
              <div key={prop.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
                {/* ── Header bien ── */}
                <div
                  className="p-5 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleExpand(prop.id)}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Building2 size={18} className="text-blue-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{prop.name}</h3>
                        {prop.full_address && (
                          <div className="flex items-start gap-1 text-xs text-gray-500 mt-0.5">
                            <MapPin size={11} className="mt-0.5 shrink-0" />
                            <span className="whitespace-pre-line leading-tight">{prop.full_address}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            prop.is_occupied ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                          }`}>
                            {prop.is_occupied ? 'Occupé' : 'Disponible'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="pt-1">
                      {isOpen
                        ? <ChevronUp size={18} className="text-gray-400" />
                        : <ChevronDown size={18} className="text-gray-400" />
                      }
                    </div>
                  </div>

                  {/* ── KPIs performance ── */}
                  {perf ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-4 border-t border-gray-100">
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">Théorique {year}</p>
                        <p className="text-xl font-bold text-gray-700">{fmtEuro(perf.ytd_theoretical)}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {fmtEuro(perf.monthly_expected)} / mois · {perf.active_months} mois sous contrat
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">Encaissé {year}</p>
                        <p className="text-xl font-bold text-green-700">{fmtEuro(perf.ytd_received)}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {perf.ytd_received >= perf.ytd_theoretical - 0.5
                            ? <span className="text-green-600">✓ Intégralité perçue</span>
                            : <span className="text-red-500">{fmtEuro(perf.ytd_theoretical - perf.ytd_received)} non encaissé</span>
                          }
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-1.5">Recouvrement</p>
                        <CollectionBar rate={perf.collection_rate} />
                      </div>
                    </div>
                  ) : (
                    <div className="pt-4 border-t border-gray-100">
                      <p className="text-xs text-gray-400">
                        Aucun bail actif : aucune donnée de performance pour {year}
                      </p>
                    </div>
                  )}
                </div>

                {/* ── Détail mensuel (expandé) ── */}
                {isOpen && perf && perf.monthly_breakdown.length > 0 && (
                  <div className="border-t border-gray-100 bg-gray-50/50 px-5 py-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                      Détail mensuel : {year}
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[640px]">
                        <thead>
                          <tr className="text-xs text-gray-400 border-b border-gray-200">
                            <th className="text-center pb-2 font-medium">Mois</th>
                            <th className="text-center pb-2 font-medium">Attendu</th>
                            <th className="text-center pb-2 font-medium">Encaissé</th>
                            <th className="text-center pb-2 font-medium">Statut</th>
                          </tr>
                        </thead>
                        <tbody>
                          {perf.monthly_breakdown.map(m => {
                            const ok = m.received > 0 && m.received >= m.expected - 0.5
                            const partial = m.received > 0 && !ok
                            const missing = m.expected - m.received

                            return (
                              <tr
                                key={m.month}
                                className="text-xs border-b border-gray-100 last:border-0"
                              >
                                <td className="py-2.5 text-gray-600 font-medium w-10 text-center">
                                  {MONTH_LABELS[m.month - 1]}
                                </td>
                                <td className="py-2.5 text-center text-gray-500 tabular-nums">
                                  {fmtEuro(m.expected)}
                                </td>
                                <td className={`py-2.5 text-center font-semibold tabular-nums ${
                                  m.received > 0 ? 'text-green-700' : 'text-gray-300'
                                }`}>
                                  {m.received > 0 ? fmtEuro(m.received) : ''}
                                </td>
                                <td className="py-2.5 text-center">
                                  {ok
                                    ? <CheckCircle2 size={14} className="text-green-500 inline" />
                                    : partial
                                    ? <span className="text-orange-500 font-medium">
                                        -{fmtEuro(missing)}
                                      </span>
                                    : <span className="text-gray-300 text-[11px]">En attente</span>
                                  }
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                        {/* Total row */}
                        <tfoot>
                          <tr className="text-xs font-bold text-gray-700 border-t-2 border-gray-200">
                            <td className="pt-2.5 pb-1 text-center">Total</td>
                            <td className="pt-2.5 pb-1 text-center tabular-nums">
                              {fmtEuro(perf.ytd_theoretical)}
                            </td>
                            <td className="pt-2.5 pb-1 text-center text-green-700 tabular-nums">
                              {fmtEuro(perf.ytd_received)}
                            </td>
                            <td className="pt-2.5 pb-1 text-center">
                              <span className={`font-semibold ${perf.collection_rate >= 90 ? 'text-green-600' : perf.collection_rate >= 65 ? 'text-yellow-600' : 'text-red-500'}`}>
                                {perf.collection_rate} %
                              </span>
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>
                )}

                {isOpen && !perf && (
                  <div className="border-t border-gray-100 px-5 py-6 text-center text-sm text-gray-400">
                    Aucune donnée de paiement pour ce bien en {year}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
