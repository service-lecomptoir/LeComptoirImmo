import { useState, useEffect, useCallback } from 'react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { Calendar, Download, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { avisEcheancesApi, type AvisEcheanceSummary } from '@/api/avis_echeances'
import { StatusBadge } from '@/components/common/StatusBadge'
import { docFilename } from '@/utils/filename'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

function statusConfig(s: string) {
  if (s === 'acquitte') return { label: 'Acquitté', variant: 'green' as const, Icon: CheckCircle, color: 'text-green-600' }
  if (s === 'envoye') return { label: 'À payer', variant: 'blue' as const, Icon: Clock, color: 'text-blue-600' }
  return { label: 'Brouillon', variant: 'gray' as const, Icon: AlertCircle, color: 'text-gray-400' }
}

export default function LocataireAvis() {
  const [avis, setAvis] = useState<AvisEcheanceSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const r = await avisEcheancesApi.list({ limit: 24 })
      setAvis(r.data)
    } catch { } finally { setIsLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const downloadPdf = (a: AvisEcheanceSummary) => {
    const token = localStorage.getItem('access_token')
    fetch(avisEcheancesApi.pdfUrl(a.id), { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const el = document.createElement('a')
        el.href = URL.createObjectURL(blob)
        el.download = docFilename('avis_echeance', { tenant: a.tenant_full_name, property: a.property_name, month: a.period_month, year: a.period_year })
        el.click()
      })
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes avis d'échéances</h1>
        <p className="text-gray-500 text-sm mt-1">Appels de loyer mensuels</p>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400 text-sm">
          Chargement…
        </div>
      ) : avis.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400">
          <Calendar size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Aucun avis d'échéance disponible</p>
          <p className="text-sm mt-1">Vos avis apparaîtront ici chaque mois.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {avis.map(a => {
            const { label, variant, Icon, color } = statusConfig(a.status)
            return (
              <div key={a.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Icon size={16} className={color} />
                    <p className="text-sm font-semibold text-gray-900">{a.period_label}</p>
                  </div>
                  <StatusBadge label={label} variant={variant} dot />
                </div>

                {/* Montants */}
                <div className="space-y-1.5 mb-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Loyer</span>
                    <span className="text-gray-900">{fmtEuro(a.amount_rent)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Charges</span>
                    <span className="text-gray-900">{fmtEuro(a.amount_charges)}</span>
                  </div>
                  {a.amount_apl && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Aide personnelle au logement déduite</span>
                      <span className="text-green-600">- {fmtEuro(a.amount_apl)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm pt-1 border-t border-gray-100">
                    <span className="font-semibold text-gray-700">Total à payer</span>
                    <span className="font-bold text-gray-900">{fmtEuro(a.amount_total)}</span>
                  </div>
                </div>

                {/* Échéance */}
                <p className="text-xs text-gray-500 mb-4">
                  Échéance : {format(new Date(a.due_date), 'd MMMM yyyy', { locale: fr })}
                </p>

                {/* Download */}
                <button
                  onClick={() => downloadPdf(a)}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50 hover:border-blue-200 hover:text-blue-700 transition-colors"
                >
                  <Download size={14} />
                  Télécharger le PDF
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
