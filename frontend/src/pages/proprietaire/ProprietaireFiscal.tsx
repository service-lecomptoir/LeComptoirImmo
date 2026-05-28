import { useState, useEffect } from 'react'
import {
  FileText, Building2, ChevronDown, ChevronUp, Printer
} from 'lucide-react'
import { apiClient } from '@/api/client'

function fmtEur(n: number) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(n)
}

interface FiscalData {
  year: number
  proprietaire_name: string
  gross_rent_revenue: number
  charges_received: number
  total_gross_revenue: number
  repairs_charges: number
  management_fees: number
  insurance_charges: number
  property_tax: number
  other_charges: number
  total_deductible: number
  net_revenue: number
  properties: Array<{
    property_id: string
    property_name: string
    address: string
    annual_rent: number
    active_leases: number
  }>
}

export default function ProprietaireFiscal() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [data, setData] = useState<FiscalData | null>(null)
  const [loading, setLoading] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  // Charges modifiables manuellement
  const [customCharges, setCustomCharges] = useState({
    repairs: 0,
    insurance: 0,
    property_tax: 0,
    other: 0,
  })

  const load = async () => {
    setLoading(true)
    try {
      const r = await apiClient.get(`/dashboard/fiscal/${year}`)
      setData(r.data)
    } catch {
      setData(null)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [year])

  const totalDeductible = data
    ? data.management_fees + customCharges.repairs + customCharges.insurance +
      customCharges.property_tax + customCharges.other
    : 0
  const netRevenue = data ? data.total_gross_revenue - totalDeductible : 0

  const printFiscal = () => {
    window.print()
  }

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Liasse fiscale — Revenus fonciers</h1>
          <p className="text-sm text-gray-500 mt-1">Déclaration 2044 simplifiée</p>
        </div>
        <div className="flex items-center gap-3 no-print">
          <select
            className="border rounded-lg px-3 py-2 text-sm font-medium"
            value={year}
            onChange={e => setYear(parseInt(e.target.value))}
          >
            {[currentYear, currentYear - 1, currentYear - 2, currentYear - 3].map(y => (
              <option key={y} value={y}>Année {y}</option>
            ))}
          </select>
          <button onClick={printFiscal}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50">
            <Printer size={16} />
            Imprimer
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full" />
        </div>
      ) : !data ? (
        <div className="text-center py-12 bg-white rounded-xl border text-gray-500">
          Aucune donnée fiscale disponible
        </div>
      ) : (
        <div className="space-y-4 print:space-y-6">
          {/* En-tête déclaration */}
          <div className="bg-white rounded-xl border p-5 print:border-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <FileText size={24} className="text-blue-600" />
              </div>
              <div>
                <h2 className="font-bold text-gray-900">Déclaration des revenus fonciers {data.year}</h2>
                <p className="text-sm text-gray-500">{data.proprietaire_name}</p>
              </div>
            </div>

            {/* Résumé fiscal */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-blue-700">{fmtEur(data.total_gross_revenue)}</p>
                <p className="text-xs text-blue-600 mt-0.5">Revenus bruts</p>
              </div>
              <div className="bg-orange-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-orange-700">{fmtEur(totalDeductible)}</p>
                <p className="text-xs text-orange-600 mt-0.5">Charges déductibles</p>
              </div>
              <div className={`rounded-lg p-3 text-center ${netRevenue >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                <p className={`text-xl font-bold ${netRevenue >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  {fmtEur(netRevenue)}
                </p>
                <p className={`text-xs mt-0.5 ${netRevenue >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {netRevenue >= 0 ? 'Revenu net imposable' : 'Déficit foncier'}
                </p>
              </div>
            </div>
          </div>

          {/* Section A — Revenus */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="bg-gray-800 text-white px-5 py-3">
              <h3 className="font-semibold text-sm">SECTION A — REVENUS BRUTS</h3>
            </div>
            <div className="p-5 space-y-3">
              <div className="flex justify-between items-center py-2 border-b">
                <div>
                  <p className="text-sm font-medium text-gray-900">Loyers encaissés</p>
                  <p className="text-xs text-gray-400">Ligne 100 — Recettes brutes</p>
                </div>
                <p className="font-bold text-gray-900">{fmtEur(data.gross_rent_revenue)}</p>
              </div>
              <div className="flex justify-between items-center py-2 border-b">
                <div>
                  <p className="text-sm font-medium text-gray-900">Provisions pour charges récupérées</p>
                  <p className="text-xs text-gray-400">Ligne 110 — Charges locatives</p>
                </div>
                <p className="font-bold text-gray-900">{fmtEur(data.charges_received)}</p>
              </div>
              <div className="flex justify-between items-center py-2 bg-gray-50 rounded-lg px-3">
                <p className="text-sm font-bold text-gray-900">Total revenus bruts (A)</p>
                <p className="text-lg font-bold text-blue-700">{fmtEur(data.total_gross_revenue)}</p>
              </div>
            </div>
          </div>

          {/* Section B — Charges */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="bg-gray-800 text-white px-5 py-3">
              <h3 className="font-semibold text-sm">SECTION B — CHARGES DÉDUCTIBLES</h3>
            </div>
            <div className="p-5 space-y-3">
              {/* Frais de gestion automatiques */}
              <div className="flex justify-between items-center py-2 border-b">
                <div>
                  <p className="text-sm font-medium text-gray-900">Frais de gestion et d'administration</p>
                  <p className="text-xs text-gray-400">Ligne 120 — 8% des loyers bruts (calculé automatiquement)</p>
                </div>
                <p className="font-bold text-gray-900">{fmtEur(data.management_fees)}</p>
              </div>

              {/* Charges saisies manuellement */}
              {[
                { key: 'repairs' as const, label: 'Travaux et réparations', line: 'Ligne 130', placeholder: '0.00' },
                { key: 'insurance' as const, label: "Primes d'assurance", line: 'Ligne 140', placeholder: '0.00' },
                { key: 'property_tax' as const, label: "Taxe foncière", line: 'Ligne 150', placeholder: '0.00' },
                { key: 'other' as const, label: 'Autres frais', line: 'Ligne 160', placeholder: '0.00' },
              ].map(({ key, label, line }) => (
                <div key={key} className="flex justify-between items-center py-2 border-b">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{label}</p>
                    <p className="text-xs text-gray-400">{line}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      value={customCharges[key]}
                      onChange={e => setCustomCharges(prev => ({ ...prev, [key]: parseFloat(e.target.value) || 0 }))}
                      className="w-28 border rounded-lg px-2 py-1 text-sm text-right font-medium"
                    />
                    <span className="text-sm text-gray-400">€</span>
                  </div>
                </div>
              ))}

              <div className="flex justify-between items-center py-2 bg-gray-50 rounded-lg px-3">
                <p className="text-sm font-bold text-gray-900">Total charges déductibles (B)</p>
                <p className="text-lg font-bold text-orange-700">{fmtEur(totalDeductible)}</p>
              </div>
            </div>
          </div>

          {/* Section C — Résultat */}
          <div className={`rounded-xl border overflow-hidden ${netRevenue >= 0 ? 'border-green-200' : 'border-red-200'}`}>
            <div className={`px-5 py-3 ${netRevenue >= 0 ? 'bg-green-700' : 'bg-red-700'} text-white`}>
              <h3 className="font-semibold text-sm">SECTION C — RÉSULTAT FISCAL</h3>
            </div>
            <div className={`p-5 ${netRevenue >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-base font-bold text-gray-900">
                    {netRevenue >= 0 ? 'Revenu foncier net imposable' : 'Déficit foncier'}
                  </p>
                  <p className="text-xs text-gray-500">A − B = Résultat à reporter sur déclaration 2042</p>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${netRevenue >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                    {fmtEur(Math.abs(netRevenue))}
                  </p>
                  {netRevenue < 0 && (
                    <p className="text-xs text-red-500 mt-0.5">Imputable sur le revenu global (plafond 10 700 €)</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Détail par bien */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50"
            >
              <div className="flex items-center gap-2">
                <Building2 size={18} className="text-blue-600" />
                <h3 className="font-semibold text-gray-900">Détail par bien immobilier</h3>
              </div>
              {showDetails ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
            </button>

            {/* Toujours dans le DOM : masqué à l'écran si replié, mais TOUJOURS imprimé */}
            <div className={`border-t ${showDetails ? '' : 'hidden print:block'}`}>
              {data.properties.length === 0 ? (
                  <p className="p-5 text-sm text-gray-400 text-center">Aucun bien rattaché</p>
                ) : (
                  <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Bien</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Adresse</th>
                        <th className="text-right px-4 py-3 text-xs font-medium text-gray-500">Loyers {data.year}</th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-gray-500">Contrats</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.properties.map(p => (
                        <tr key={p.property_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">{p.property_name}</td>
                          <td className="px-4 py-3 text-gray-500 text-xs">{p.address}</td>
                          <td className="px-4 py-3 text-right font-semibold text-gray-900">{fmtEur(p.annual_rent)}</td>
                          <td className="px-4 py-3 text-center">
                            <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full text-xs">
                              {p.active_leases}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-gray-50 border-t">
                      <tr>
                        <td colSpan={2} className="px-4 py-3 font-bold text-gray-900">Total</td>
                        <td className="px-4 py-3 text-right font-bold text-blue-700">{fmtEur(data.gross_rent_revenue)}</td>
                        <td />
                      </tr>
                    </tfoot>
                  </table>
                  </div>
                )}
            </div>
          </div>

          {/* Note légale */}
          <div className="bg-gray-50 border rounded-xl p-4 text-xs text-gray-500">
            <p className="font-medium text-gray-600 mb-1">⚠️ Note importante</p>
            <p>Ce document est une aide à la déclaration fiscale à titre indicatif. Les frais de gestion sont estimés à 8% des loyers bruts. Complétez les charges réelles (travaux, assurance, taxe foncière) pour obtenir le résultat définitif. Consultez un expert-comptable pour votre déclaration officielle.</p>
          </div>
        </div>
      )}
    </div>
  )
}
