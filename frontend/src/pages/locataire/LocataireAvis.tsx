import { useState, useEffect, useCallback } from 'react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { Calendar, Download, CheckCircle, Clock, AlertCircle, CalendarClock, Send } from 'lucide-react'
import { avisEcheancesApi, type AvisEcheanceSummary } from '@/api/avis_echeances'
import { apurementApi, type ApurementPlan } from '@/api/apurement'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Button } from '@/components/ui'
import { docFilename } from '@/utils/filename'
import { downloadBlob } from '@/utils/download'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'

import { formatEuro as fmtEuro } from '@/utils/format'

function statusConfig(s: string) {
  if (s === 'acquitte') return { label: 'Acquitté', variant: 'green' as const, Icon: CheckCircle, color: 'text-green-600' }
  if (s === 'envoye') return { label: 'À payer', variant: 'blue' as const, Icon: Clock, color: 'text-blue-600' }
  return { label: 'Brouillon', variant: 'gray' as const, Icon: AlertCircle, color: 'text-gray-400' }
}

export default function LocataireAvis() {
  const [avis, setAvis] = useState<AvisEcheanceSummary[]>([])
  const [plans, setPlans] = useState<ApurementPlan[]>([])
  const [declaring, setDeclaring] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const [r, p] = await Promise.allSettled([
        avisEcheancesApi.list({ limit: 24 }),
        apurementApi.mine(),
      ])
      if (r.status === 'fulfilled') setAvis(r.value.data)
      if (p.status === 'fulfilled') setPlans(p.value.data.filter(x => x.status === 'active'))
    } catch { } finally { setIsLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const declareInst = async (planId: string, seq: number) => {
    setDeclaring(`${planId}-${seq}`)
    try {
      await apurementApi.declareInstallment(planId, seq)
      toast.success('Paiement déclaré : votre gestionnaire le validera à réception.')
      await load()
    } catch (e: any) {
      toast.error(getErrorMessage(e, 'Déclaration impossible'))
    } finally { setDeclaring(null) }
  }

  const downloadPlanPdf = (p: ApurementPlan) =>
    apurementApi.downloadPdf(p.id, docFilename('plan_apurement', { tenant: p.tenant_name || '', property: p.property_name || '' }))

  const downloadPdf = async (a: AvisEcheanceSummary) => {
    try {
      const token = localStorage.getItem('access_token')
      const r = await fetch(avisEcheancesApi.pdfUrl(a.id), { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) { toast.error('Avis indisponible au téléchargement.'); return }
      const blob = await r.blob()
      downloadBlob(blob, docFilename('avis_echeance', { tenant: a.tenant_full_name, property: a.property_name, month: a.period_month, year: a.period_year }))
    } catch {
      toast.error('Téléchargement impossible (erreur réseau).')
    }
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes avis d'échéances</h1>
        <p className="text-gray-500 text-sm mt-1">Appels de loyer mensuels</p>
      </div>

      {/* ── Plans d'apurement (échéanciers d'impayés) ── */}
      {plans.map(p => {
        const todayIso = new Date().toISOString().slice(0, 10)
        return (
          <div key={p.id} className="mb-6 bg-white rounded-xl border border-amber-200 p-5">
            <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
              <div className="flex items-center gap-2">
                <CalendarClock size={18} className="text-amber-600" />
                <div>
                  <p className="font-semibold text-gray-900">{p.label || "Plan d'apurement"}</p>
                  <p className="text-xs text-gray-500">
                    Reste à régler <span className="font-semibold text-gray-700">{fmtEuro(p.remaining)}</span> sur {fmtEuro(p.total_amount)} · {p.paid_count}/{p.count} échéance(s) réglée(s)
                  </p>
                </div>
              </div>
              <button onClick={() => downloadPlanPdf(p)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50">
                <Download size={13} /> PDF
              </button>
            </div>
            <div className="divide-y divide-gray-100">
              {p.installments.map(inst => {
                const overdue = !inst.paid && inst.due_date < todayIso
                return (
                  <div key={inst.seq} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="text-sm">
                      <span className="font-medium text-gray-800">Échéance {inst.seq}</span>
                      <span className={`ml-2 ${overdue ? 'text-red-600' : 'text-gray-500'}`}>
                        {format(new Date(inst.due_date), 'd MMM yyyy', { locale: fr })}
                        {overdue && ' · en retard'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-gray-900">{fmtEuro(inst.amount)}</span>
                      {inst.paid ? (
                        <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700 inline-flex items-center gap-1"><CheckCircle size={11} /> Payé</span>
                      ) : inst.declared ? (
                        <span className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700 inline-flex items-center gap-1"><Clock size={11} /> En attente de validation</span>
                      ) : (
                        <Button variant="primary" size="sm" onClick={() => declareInst(p.id, inst.seq)}
                          isLoading={declaring === `${p.id}-${inst.seq}`} leftIcon={<Send size={12} />}>
                          {declaring === `${p.id}-${inst.seq}` ? 'Envoi…' : 'Déclarer le paiement'}
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}

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
